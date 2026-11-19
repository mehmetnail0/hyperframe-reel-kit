#!/usr/bin/env python3
"""Planner: transcript + shots + vocabulary + memory -> plan.json (ONE model call).

Model slot is pluggable (models.json). Adapters:
  claude   `claude -p` CLI (Claude Code, default; uses the session's own login)
  anthropic  Messages API via ANTHROPIC_API_KEY            (adapter ready, off unless enabled)
  openai     Chat Completions via OPENAI_API_KEY           (adapter ready, off unless enabled)
  gemini     generateContent via GEMINI_API_KEY            (adapter ready, off unless enabled)
  local      no model: keyword heuristics + seeded variety (fast fallback, ~0.1 s)
Paid third-party adapters refuse to run unless models.json sets "enabled": true for them.
"""
import json, os, random, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB = json.load(open(os.path.join(HERE, "vocab.json")))


def load_cfg():
    return json.load(open(os.path.join(HERE, "models.json")))


# ------------------------------------------------------------------ prompt
def build_prompt(words, segs, shots, memory, opts):
    tx = []
    for s in segs:
        ws = " ".join(f"{i}:{words[i]['w']}" for i in range(s["i0"], s["i1"]))
        tx.append(f"[{s['t']:.1f}-{s['e']:.1f}s] {ws}")
    recent = memory.get("recent", [])[-3:]
    rec_txt = "\n".join(f"- {r['reel']}: types {r['types']}; enter {r['enter']}; exit {r['exit']}; camera {r['camera']}; headers {r['headers']}"
                        for r in recent) or "- (none yet)"
    scenes = "\n".join(f"  {k}: fields {v['fields']} — use: {v['use']}" for k, v in VOCAB["scenes"].items())
    g = open(os.path.join(HERE, "prompts", "grammar.md")).read()
    return f"""You are the motion editor of a vertical talking-head reel in the "split-motion / Kallaway" style.
Write the reel PLAN as one JSON object. Output ONLY the JSON (no prose, no code fences).

{g}

TARGET: final length {opts['min_len']}-{opts['max_len']} s of speech (the raw is {words[-1]['e']:.0f} s). Topic hint: {opts.get('topic') or 'infer it'}.
Theme: {opts.get('theme', 'dark')}. Seed: {opts['seed']}.

SCENE TYPES (scene.type):
{scenes}
ENTER verbs: {VOCAB['enter']}
EXIT verbs: {VOCAB['exit']}
CAMERA: {VOCAB['camera']}
HEADER styles: {VOCAB['header_styles']}   (markup inside text: *serif italic*, [red box], _underline_)
ICONS (scene.type=icon): {VOCAB['icons']}
3D presets (scene.type=hero3d): {VOCAB['three_presets']}

NOVELTY — the last reels used these; do NOT repeat their combinations, pick other types/verbs/cameras where it fits:
{rec_txt}
Also include at least ONE custom_svg scene: draw a NEW line-art illustration for a concept in this script
(svg viewBox "0 0 900 800", <= 40 elements, stroke="#fff" or "#e8283c", stroke-width 4-8, fill="none" for lines,
class="p" on shapes that should pop; no text longer than 3 words; no images/scripts).

TRANSCRIPT (word index:word), one line per sentence:
{chr(10).join(tx)}

SHOTS (camera changes, seconds): {[s['t0'] for s in shots['shots']]}

JSON SCHEMA:
{{
 "title": "3-6 words",
 "theme": "dark|light", "accent2": "#hex from {VOCAB['accent2']}",
 "keep": [[first_word_index, last_word_index], ...],      // story cut, whole sentences, in order
 "emph": [word_index, ...],                                // 4-10 words shown in serif italic in captions
 "beats": [                                                 // cover the KEPT words in order; beat = 1.5-3.5 s
   {{"w0": first_word_index_of_beat, "layout": "split|speaker|graphic",
     "header": {{"text": "2-6 words", "style": "box|underline|serif|plain"}},   // only when a section starts
     "hero": true,                                           // only 2-4 beats per reel: the strongest moments
     "scene": {{"type": "...", "enter": "...", "exit": "...", "camera": "none|push|pull|parallax|tilt (hero beats only)", ...type fields..., "at": [word_index per item]}},
     "sfx": ["flash"|"reveal"|"ding"]                       // optional, rare
   }}
 ]
}}
Rules for beats: first beat w0 = first kept word; split ~70 % of the time; speaker beats (no scene) 1.5-4 s every 4-8 s
on punchlines; graphic <= 1 beat; chapters (type chapter) when the speaker enumerates; 1-2 hero3d only on the strongest
concrete object; list/steps/counter items reveal on the word that says them ("at").

MOTION LANGUAGE (round-2 feedback from the owner — obey it):
- Stillness is the default. An object arrives with a soft eased settle (tiny overshoot), then HOLDS. No sliding, no
  constant drifting. Fluidity comes from the quality of easing and timing, not from movement.
- camera must be "none" except on the 2-4 "hero": true beats, where ONE slow push / pull / parallax / tilt is allowed.
- Vary enter verbs per scene (settle, pop, focus, bloom, iris, wipe, unfold, tilt3d, flipY, zoomIn, fall); exits are quiet
  (fade, dissolve, recede, lift, collapse, irisOut).

LESS LITERAL TEXT (round-2 feedback — obey it):
- The captions already show every spoken word. A scene must NOT repeat the caption words as on-screen text.
- Give the visual SUBSTANCE: an illustrative object (icon = a lit glass object, custom_svg drawing, 3D, phone, doc,
  grid of thumbnails, chart), light, depth, a number. The compiler adds glow, particles and a cinematic shine itself.
- Text only where it adds: the section header, a number (counter), or ONE key word that is not being said right then.
  Leave "label" empty unless it adds something the voice does not say. Items in list/steps/tree may be 1-2 words.
- The motion panel is now shorter (the speaker card is taller): fewer, bigger elements per scene.
"""


# ------------------------------------------------------------------ adapters
def _json_from(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in model output")
    return json.loads(m.group(0))


def call_claude(prompt, cfg):
    cmd = ["claude", "-p", "--output-format", "json"]
    if cfg.get("model"):
        cmd += ["--model", cfg["model"]]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=cfg.get("timeout", 600))
    out = json.loads(r.stdout)
    return out.get("result", ""), {"cost_usd": out.get("total_cost_usd"), "api_ms": out.get("duration_api_ms")}


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def call_anthropic(prompt, cfg):
    j = _post("https://api.anthropic.com/v1/messages", {"model": cfg["model"], "max_tokens": 16000,
              "messages": [{"role": "user", "content": prompt}]},
              {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}, cfg.get("timeout", 600))
    return "".join(c.get("text", "") for c in j["content"]), {"usage": j.get("usage")}


def call_openai(prompt, cfg):
    j = _post("https://api.openai.com/v1/chat/completions", {"model": cfg["model"], "messages": [{"role": "user", "content": prompt}],
              "response_format": {"type": "json_object"}}, {"authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}, cfg.get("timeout", 600))
    return j["choices"][0]["message"]["content"], {"usage": j.get("usage")}


def call_gemini(prompt, cfg):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['model']}:generateContent?key={os.environ['GEMINI_API_KEY']}"
    j = _post(url, {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}, {}, cfg.get("timeout", 600))
    return j["candidates"][0]["content"]["parts"][0]["text"], {"usage": j.get("usageMetadata")}


def call_openrouter(prompt, cfg):
    """OpenRouter (any model id). Key read from ~/.config/tigno/openrouter.key at call time only (never in git/env dumps).
    No response_format=json_object (gemini-4-carbon failed with it + max_tokens 16000); plain call, max_tokens 32000."""
    key = open(os.path.expanduser(cfg.get("key_file", "~/.config/tigno/openrouter.key"))).read().strip()
    body = {"model": cfg["model"], "messages": [{"role": "user", "content": prompt}], "max_tokens": cfg.get("max_tokens", 32000)}
    j = _post("https://openrouter.ai/api/v1/chat/completions", body, {"authorization": "Bearer " + key}, cfg.get("timeout", 600))
    return j["choices"][0]["message"]["content"], {"usage": j.get("usage"), "model": j.get("model")}


ADAPTERS = {"claude": call_claude, "anthropic": call_anthropic, "openai": call_openai, "gemini": call_gemini,
            "openrouter": call_openrouter}


def repair_json(text):
    """cheap local repair: code fences, trailing commas, comments, unbalanced closers (truncation)."""
    t = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M)
    t = re.sub(r"//[^\n\"]*$", "", t, flags=re.M)
    t = re.sub(r",\s*([}\]])", r"\1", t)
    m = re.search(r"\{.*", t, re.S)
    t = m.group(0) if m else t
    try:
        return json.loads(t[:t.rindex("}") + 1])
    except Exception:
        pass
    stack, out, ins, esc_ = [], [], False, False
    for ch in t:
        out.append(ch)
        if ins:
            esc_ = (ch == "\\" and not esc_)
            if ch == '"' and not esc_:
                ins = False
            continue
        if ch == '"':
            ins = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    s2 = "".join(out).rstrip().rstrip(",")
    if ins:
        s2 += '"'
    return json.loads(re.sub(r",\s*([}\]])", r"\1", s2 + "".join(reversed(stack))))


# ------------------------------------------------------------------ local heuristic planner
KEYICON = [(r"money|paid|pay|cash|dollar|\$|rich|contract", "money"), (r"time|wait|later|years?|months?|days?", "hourglass"),
           (r"idea|think|smart|know", "bulb"), (r"goal|target|aim", "target"), (r"grow|growth|scale|up", "chart"),
           (r"follow|audience|people|fans|community", "users"), (r"video|content|post|clip|watch", "play"),
           (r"camera|film|shoot", "camera"), (r"talk|say|voice|podcast|mic", "mic"), (r"lock|secret|private", "lock"),
           (r"win|best|top|champion", "trophy"), (r"fire|hot|viral|blow", "fire"), (r"love|heart|like", "heart"),
           (r"warn|careful|mistake|wrong|stop", "warning"), (r"step|climb|level|ladder|top", "mountain"),
           (r"search|find|look", "search"), (r"message|dm|text|ask", "chat"), (r"brain|mind|mental", "brain"),
           (r"plan|calendar|consistent|every day|daily", "calendar"), (r"key|unlock|answer", "key"), (r"star|famous|celebrity", "star")]
STOP = set("the a an and or but so to of in on at for with is are was were be been it this that i you he she we they my your "
           "me him her them our their just like really very do does did have has had not no yes if then than there here what "
           "when who how why all can will would could should gonna got get going know mean thing things".split())


def local_plan(words, segs, shots, memory, opts):
    R = random.Random(opts["seed"])
    # story: keep sentences (drop very short fillers) until max_len
    keep, tot = [], 0.0
    for s in segs:
        d = s["e"] - s["t"]
        if s["i1"] - s["i0"] < 3 and tot > 5:
            continue
        if tot + d > opts["max_len"]:
            break
        keep.append([s["i0"], s["i1"] - 1])
        tot += d
    kept = [i for a, b in keep for i in range(a, b + 1)]
    beats, i, n = [], 0, len(kept)
    used_types = []
    recent_types = {t for r in memory.get("recent", [])[-2:] for t in r["types"]}
    pool = [t for t in ["icon", "quote", "orbit", "grid", "doc", "bars", "steps", "radar", "tree", "browser", "phone", "network", "custom_svg"]]
    pool.sort(key=lambda t: (t in recent_types, R.random()))
    k = 0
    while i < n:
        j = i
        t0 = words[kept[i]]["t"]
        while j + 1 < n and words[kept[j + 1]]["e"] - t0 < R.uniform(1.8, 3.2):
            j += 1
        span = [words[kept[x]]["w"] for x in range(i, j + 1)]
        text = " ".join(span).lower()
        layout = "speaker" if (k % R.choice([3, 4]) == 2 and k > 1) else "split"
        b = {"w0": kept[i], "layout": layout}
        if layout != "speaker":
            nums = re.findall(r"\b(\d[\d,.]*)\b", text)
            if nums:
                sc = {"type": "counter", "value": float(nums[0].replace(",", "")), "label": " ".join(w for w in span if w.lower() not in STOP)[:24]}
            else:
                typ = pool[k % len(pool)]
                kw = [w.strip(".,?!\"'").lower() for w in span if w.lower().strip(".,?!") not in STOP and len(w) > 2]
                if typ == "icon":
                    ic = next((ic for pat, ic in KEYICON if re.search(pat, text)), R.choice(VOCAB["icons"]))
                    sc = {"type": "icon", "icon": ic, "label": (kw[0] if kw else "")}
                elif typ == "quote":
                    sc = {"type": "quote", "text": " ".join(kw[:3]) + (f" *{kw[3]}*" if len(kw) > 3 else "")}
                elif typ in ("orbit", "network"):
                    sc = {"type": typ, "center": (kw[0] if kw else "you"), "items": kw[1:5] or ["", "", ""]}
                elif typ in ("doc", "browser"):
                    sc = {"type": typ, "title": (kw[0].title() if kw else "Plan"), "rows": kw[1:4] or ["Hook", "Body", "CTA"]}
                elif typ in ("steps", "tree"):
                    sc = {"type": typ, "items": kw[:3] or ["start", "grow", "win"], "root": kw[0] if kw else "start", "children": kw[1:3] or ["a", "b"]}
                elif typ == "bars":
                    sc = {"type": "bars", "values": [25, 45, 70, 95], "labels": kw[:4]}
                elif typ == "custom_svg":
                    sc = {"type": "custom_svg", "svg": '<svg viewBox="0 0 900 800"><path d="M150 600 C 300 200, 600 200, 750 600" stroke="#fff" stroke-width="8" fill="none"/>'
                                                       '<circle class="p" cx="750" cy="600" r="30" fill="#e8283c"/></svg>', "label": kw[0] if kw else ""}
                else:
                    sc = {"type": typ, "label": kw[0] if kw else ""}
            sc.update(enter=R.choice(VOCAB["enter"]), exit=R.choice(VOCAB["exit"]), camera=R.choice(VOCAB["camera"]))
            b["scene"] = sc
            used_types.append(sc["type"])
            if k % 4 == 0:
                kw2 = [w.strip(".,?!\"'") for w in span if w.lower().strip(".,?!") not in STOP][:3]
                if kw2:
                    kw2[-1] = f"*{kw2[-1]}*"
                    b["header"] = {"text": " ".join(kw2), "style": R.choice(VOCAB["header_styles"])}
        beats.append(b)
        i = j + 1
        k += 1
    return {"title": opts.get("topic") or "reel", "theme": opts.get("theme", "dark"), "accent2": R.choice(VOCAB["accent2"]),
            "keep": keep, "emph": [], "beats": beats}


# ------------------------------------------------------------------ validate / repair
STOPW = set("the a an and or but so to of in on at for with is are was were be been it this that i you he she we they my your "
            "me him her them our their just like really very do does did have has had not no yes if then than there here what "
            "when who how why all can will would could should gonna got get going know mean thing things it's that's don't".split())
TEXT_FIELDS = ("label", "text", "center", "title", "headline", "sub", "root")
LIST_FIELDS = ("items", "rows", "children")


def _toks(x):
    return [t for t in re.findall(r"[a-z0-9$%']+", str(x).lower().replace("*", "").replace("[", "").replace("]", ""))
            if t not in STOPW and len(t) > 2 and not t.isdigit()]


def dup_text(plan, words):
    """flag scene text that echoes the caption words of its beat (+-1 beat); strip echoing labels."""
    bs = plan["beats"]
    ws = [b["w0"] for b in bs] + [len(words)]
    flags = []
    for k, b in enumerate(bs):
        sc = b.get("scene")
        if not sc:
            continue
        lo, hi = ws[max(0, k - 1)], ws[min(len(bs), k + 2)]
        cap = {t for w in words[lo:hi] for t in _toks(w["w"])}
        for f in TEXT_FIELDS + LIST_FIELDS:
            v = sc.get(f)
            vals = v if isinstance(v, list) else [v]
            for x in vals:
                x = x.get("label", "") if isinstance(x, dict) else x
                tk = _toks(x or "")
                if len(tk) >= 1 and sum(t in cap for t in tk) / len(tk) >= .6 and (len(tk) >= 2 or f in TEXT_FIELDS):
                    flags.append(dict(beat=k, field=f, text=str(x)[:40]))
        # auto-fix: echoing labels / subtitles go (lists stay: they are structure, 1-2 words each)
        for f in ("label", "sub", "title", "center"):
            if any(fl["beat"] == k and fl["field"] == f for fl in flags):
                sc[f] = ""
        if sc.get("type") == "quote" and any(fl["beat"] == k and fl["field"] == "text" for fl in flags):
            sc.update(type="icon", icon=sc.get("icon", "star"), label="")
            for fl in flags:
                if fl["beat"] == k and fl["field"] == "text":
                    fl["fix"] = "quote -> glass object"
    return flags


def validate(plan, words):
    fixes = []
    nW = len(words)
    plan.setdefault("keep", [[0, nW - 1]])
    plan["keep"] = [[max(0, min(nW - 1, int(a))), max(0, min(nW - 1, int(b)))] for a, b in plan["keep"] if int(b) >= int(a)]
    kept = sorted({i for a, b in plan["keep"] for i in range(a, b + 1)})
    ks = set(kept)
    bs = []
    for b in plan.get("beats", []):
        w0 = int(b.get("w0", 0))
        if w0 not in ks:
            nxt = [i for i in kept if i >= w0]
            if not nxt:
                fixes.append(f"drop beat w0={w0} (after cut)")
                continue
            fixes.append(f"beat w0 {w0}->{nxt[0]}")
            w0 = nxt[0]
        b["w0"] = w0
        L = b.get("layout", "split")
        if L not in VOCAB["layouts"]:
            b["layout"] = "split"
        sc = b.get("scene")
        if b["layout"] != "speaker":
            if not sc or sc.get("type") not in VOCAB["scenes"]:
                fixes.append(f"beat {w0}: scene {sc and sc.get('type')} -> icon")
                sc = {"type": "icon", "icon": "star", **({} if not sc else {k: v for k, v in sc.items() if k != 'type'})}
            for f, opts in (("enter", VOCAB["enter"]), ("exit", VOCAB["exit"]), ("camera", VOCAB["camera"])):
                if sc.get(f) not in opts:
                    sc[f] = opts[0]
            b["scene"] = sc
        bs.append(b)
    bs.sort(key=lambda b: b["w0"])
    uniq = []
    for b in bs:
        if uniq and b["w0"] == uniq[-1]["w0"]:
            fixes.append(f"merge duplicate beat at {b['w0']}")
            continue
        uniq.append(b)
    if uniq and uniq[0]["w0"] != kept[0]:
        uniq[0]["w0"] = kept[0]
    plan["beats"] = uniq
    plan["emph"] = [int(i) for i in plan.get("emph", []) if int(i) in ks]
    # motion budget: continuous camera only on hero beats, at most ~1 per 6 beats (2-4 per reel)
    heroes = [b for b in uniq if b.get("hero") or (b.get("scene") or {}).get("hero")]
    cap = max(2, min(4, round(len(uniq) / 6)))
    if len(heroes) > cap:
        for b in heroes[cap:]:
            b["hero"] = False
            (b.get("scene") or {}).pop("hero", None)
        fixes.append(f"hero beats capped {len(heroes)}->{cap}")
    if not heroes:  # pick the strongest-looking scenes: 3D / chapter / counter / custom_svg first
        rank = {"hero3d": 0, "chapter": 1, "counter": 2, "custom_svg": 3, "network": 4, "orbit": 5}
        cand = sorted([b for b in uniq if b.get("scene")], key=lambda b: rank.get(b["scene"]["type"], 9))[:cap]
        for b in cand:
            b["hero"] = True
    for b in uniq:
        sc = b.get("scene")
        if sc and not (b.get("hero") or sc.get("hero")) and sc.get("camera", "none") != "none":
            sc["camera"] = "none"
    flags = dup_text(plan, words)
    if flags:
        fixes.append(f"duplicate-caption text in {len({f['beat'] for f in flags})} beat(s): " +
                     "; ".join(f"b{f['beat']}.{f['field']}='{f['text']}'" for f in flags[:8]))
    plan["_dup_text_flags"] = flags
    return plan, fixes


def make_plan(words, segs, shots, memory, opts, adapter=None):
    cfg = load_cfg()
    name = adapter or cfg["default"]
    t0 = time.time()
    meta = {"adapter": name}
    if name == "local":
        plan = local_plan(words, segs, shots, memory, opts)
    else:
        a = cfg["adapters"][name]
        if name != "claude" and not a.get("enabled"):
            raise SystemExit(f"adapter {name} is disabled in models.json (paid API) — enable it explicitly to trial it")
        prompt = build_prompt(words, segs, shots, memory, opts)
        meta["prompt_chars"] = len(prompt)
        text, info = ADAPTERS[name](prompt, a)
        meta.update(info or {})
        try:
            plan = _json_from(text)
        except Exception as ex:
            try:
                plan = repair_json(text)
                meta["json_repair"] = "local"
            except Exception:
                try:  # one retry: send the broken JSON back to the same model to fix
                    fix_prompt = ("Your previous answer was not valid JSON (" + str(ex)[:200] + "). Return ONLY the corrected JSON "
                                  "object, nothing else:\n" + text[:60000])
                    text2, info2 = ADAPTERS[name](fix_prompt, a)
                    plan = repair_json(text2)
                    meta["json_repair"] = "model retry"
                except Exception as ex2:
                    meta["error"] = f"bad JSON from model ({ex2}); fell back to local"
                    plan = local_plan(words, segs, shots, memory, opts)
    plan, fixes = validate(plan, words)
    plan["seed"] = opts["seed"]
    meta.update(s=round(time.time() - t0, 1), fixes=fixes)
    return plan, meta


if __name__ == "__main__":
    work = sys.argv[1]
    w = json.load(open(os.path.join(work, "words.json")))
    sh = json.load(open(os.path.join(work, "shots.json")))
    print(build_prompt(w["words"], w["segments"], sh, {}, {"min_len": 55, "max_len": 75, "seed": 1}))
