#!/usr/bin/env python3
"""Round-3 Claude stages (claude CLI only — no paid API keys):

  director(words, segs, opts)              ONE call (Opus 5.5, effort high) -> storyboard (JSON)
  code_sections(story, words, G, model)    ONE call PER SECTION, all in parallel -> {sid: JS body}
  repair(sid, code, report, ...)           feed validator errors back to the same coder model
Every call is measured: wall seconds, input/output/cache tokens, cost (as reported by the CLI).
"""
import json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5"}
SYS = ("You are a senior motion designer and front-end engineer. You answer with exactly the requested artifact and nothing else. "
       "No tools are available; do not ask questions.")


def call(prompt, model="opus", effort="high", timeout=1200):
    t0 = time.time()
    cmd = ["claude", "-p", "--output-format", "json", "--model", MODELS.get(model, model), "--effort", effort,
           "--system-prompt", SYS, "--tools", ""]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    try:
        j = json.loads(r.stdout)
    except Exception:
        raise RuntimeError(f"claude CLI failed: {r.stdout[-400:]} {r.stderr[-400:]}")
    u = j.get("usage") or {}
    meta = dict(model=MODELS.get(model, model), effort=effort, s=round(time.time() - t0, 1), api_ms=j.get("duration_api_ms"),
                cost_usd=j.get("total_cost_usd"), in_tok=u.get("input_tokens", 0), out_tok=u.get("output_tokens", 0),
                cache_read=u.get("cache_read_input_tokens", 0), cache_write=u.get("cache_creation_input_tokens", 0))
    return j.get("result", ""), meta


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def _code(text):
    m = re.search(r"```(?:js|javascript)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


GRAMMAR = open(os.path.join(os.path.dirname(HERE), "prompts", "grammar.md")).read()
VERDICT = """OWNER'S VERDICT ON EARLIER ROUNDS (obey):
- Round 1: everything slid/drifted all the time; scenes repeated the caption words as text. Fluidity must come from QUALITY,
  not constant movement. Visuals must be more satisfying and organic than literal text.
- Round 2: things arrived one by one, each a small standalone object (icon+label, counter, quote, glowing orb) replaced every
  ~2 s; glow was local/patchy ("glowing balls"); boring; all plans looked alike. He wants Kallaway's FULL, continuous dynamic:
  the panel is always rich, one hero structure per section that keeps EVOLVING word by word, sub-events between, but no drifting.
"""


def director(words, segs, opts, model="opus", effort="high"):
    tx = "\n".join(f"[{s['t']:.1f}-{s['e']:.1f}s] " + " ".join(f"{i}:{words[i]['w']}" for i in range(s["i0"], s["i1"])) for s in segs)
    prompt = f"""{VERDICT}
{GRAMMAR}

You are the DIRECTOR of a vertical talking-head reel (split layout: motion panel on top, tall speaker card below, 1-3 word captions
at the seam). Write the STORYBOARD as ONE JSON object, nothing else.

TARGET speech length {opts['min_len']}-{opts['max_len']} s (raw is {words[-1]['e']:.0f} s). Topic hint: {opts.get('topic') or 'infer'}.

DESIGN RULES
1. Split the kept talk into SECTIONS of 8-25 s. Each section has ONE persistent HERO STRUCTURE that EVOLVES with the words:
   rows build, cells fill, nodes connect, numbers count, the highlight moves, the camera pushes in/tilts on a beat.
   Think Kallaway: a script document whose colour-coded highlighter rows build one by one; a creator profile whose post grid
   fills; a streak calendar ticking; a branch tree/pipeline growing; a phone feed with real-looking cards; an orbit of thumbnail
   cards around a red pill; a chart building; numbered rows with blurred unrevealed rows; a network of avatars with a counter
   chip; a contract/offer card being filled and signed; stacked pages fanning out. You may invent other structures.
   NEVER the same structure in two consecutive sections. Content must come from the transcript's actual claims and look real
   (names, handles, numbers, labels, row titles) - but never repeat the spoken caption words as text.
2. The panel is ALWAYS FULL: background light field + midground hero + foreground accents (chips, small cards, connectors,
   numbers) arriving in staggered groups. At least 3 elements alive at any time; never one lonely object.
3. ONE LIGHT MODEL per section: key light position (x 0-1080, y 0-{opts['panel_h']}) + temperature; everything is lit by it.
   No glowing balls, no isolated halos.
4. TRANSITIONS BY TRANSFORMATION between sections (push through an element of the old hero into the new one, match cut, zoom
   into a cell that becomes the next hero). No blank panel.
5. EVENTS: anchor every evolution step to the word index where it is said. Aim 40-60 panel events per minute counting
   sub-events (a new hero step every 1.5-3 s, small sub-events between). kind: "major" (hero evolution / chapter: a soft riser
   lands on it), "item" (a row/cell/node/card added: tiny tick), "minor" (highlight, chip, count, camera move).
6. Full-screen speaker runs: 2-4 s on the strongest opinion lines, one every ~8-12 s (the panel hides during them).
7. One header per section: 2-5 words, bold sans + ONE *serif italic* accent word (markup *word*); optionally put ONE other
   word in square brackets to render it in a red highlight box, e.g. "Why creators *quit* [early]". Never write the words 'red box'.

TRANSCRIPT (word index:word):
{tx}

JSON SCHEMA
{{"title": "...",
 "keep": [[first_word_index, last_word_index], ...],
 "emph": [word_index, ...],
 "speaker": [[w0, w1], ...],
 "sections": [
  {{"w0": first_word_index, "w1": last_word_index,
    "header": {{"text": "..."}},
    "hero": {{"structure": "short name", "concept": "what it shows and how it evolves, 1-2 sentences",
             "content": {{ "...": "real-looking labels / names / numbers / rows the coder will render" }}}},
    "supporting": "foreground accents and their arrival groups",
    "light": {{"x": 0, "y": 0, "temp": "warm|cool|neutral|red|gold|green|violet"}},
    "camera": "where the camera pushes / tilts and on which word",
    "transition_out": "how this hero transforms into the next one",
    "events": [{{"w": word_index, "kind": "major|item|minor", "what": "..."}}]
  }}]}}
"""
    text, meta = call(prompt, model, effort)
    return _json(text), meta, prompt


def coder_prompt(story, k, words, G, lib_src):
    s = story["sections"][k]
    prev = story["sections"][k - 1]["hero"]["structure"] if k else None
    nxt = story["sections"][k + 1]["hero"]["structure"] if k + 1 < len(story["sections"]) else None
    ws = "\n".join(f"{i}: {words[i]['w']} @ {words[i]['t']:.2f}s" for i in range(s["w0"], min(len(words), s["w1"] + 1)))
    return f"""{VERDICT}
You are the SCENE CODER for ONE section of a vertical reel. Write bespoke GSAP motion for this section using the R3 helper
library below (helpers are building blocks, not a menu: compose them, nest them, restyle them, add your own DOM with R3.mk).

SECTION STORYBOARD (from the director):
{json.dumps(s, indent=1, ensure_ascii=False)}
Previous section hero: {prev}. Next section hero: {nxt}.
Section time: S = {s['_t0']:.2f}s to E = {s['_t1']:.2f}s (absolute). Word times (index: word @ time) — use W[index] in code:
{ws}

STAGE: the panel is 1080 x {G['panel_h']} px. Header text (rendered for you) occupies y 140-{G['stage_top'] - 10}.
Your structures live in x 30..1050, y {G['stage_top']}..{G['cap_top'] - 20} (the caption sits at y {G['cap_top']}). Keep EVERYTHING inside.
The compositor already handles: section fade/scale in and push-through out (last 0.45 s), the header, captions, SFX.

HARD RULES
- Panel always FULL: build the hero + supporting accents so that >= 3 elements (class r3-el; all R3 helpers set it) are visible
  at every moment from S+0.5 to E-0.45, and never a single lonely object. Group arrivals with stagger + overshoot (R3.appear).
- Evolve the hero on the words: schedule each step at W[i] (minus 0.05). 40-60 panel events per minute incl. sub-events.
- Between events NOTHING moves. Forbidden: yoyo, repeat, blinking/"live" pulses, ticking clocks, idle floating, any tween longer
  than 1.2 s — except at most ONE eased camera move per section (ctx.cam.push or ctx.cam.tilt, <= 2.5 s) on a major event.
  (QC measures ambient motion in the holds; > 20 % fails the render.)
- Text lines must never overlap each other: leave >= 8 px between lines/rows; keep UI text <= 2 short lines per card.
- NO GLOW, NO SLAB, NO DUST (owner's hard rule, the render FAILS otherwise): no radial-gradient, no blurred blobs, no soft
  light glow behind objects, no grey glowing panel behind a diagram, no floating particles/orbs/dots. The background stays the
  flat deep colour with its hairline grid. ALL light and depth come from the content itself: strokes, solid/linear fills, the
  card rim/sheen R3 already applies, and shadows WITH real offsets (e.g. '0 18px 40px rgba(0,0,0,.5)'). Blur only as a brief
  transition state (from-state of a tween), never resting.
- ALWAYS DYNAMIC: something meaningful changes at least every ~0.5-1 s (a row builds, a value updates, a node connects, a
  highlight moves); never 'diagram then wait'. Still no drifting: changes are discrete, eased events.
- No text that repeats the spoken words; real-looking UI text, names, numbers, labels only.
- Deterministic: no Math.random, no Date. Everything scheduled on `tl` at absolute times between S and E.
- Anything inside a phone/device must stay inside its screen.
- Output ONLY the JavaScript function BODY in one ```js block. In scope: ctx, R3, tl, W, S, E, G (ctx.mid, ctx.fg layers; ctx.cam rig).

R3 LIBRARY SOURCE (read it, use its signatures exactly):
```js
{lib_src}
```
"""


def code_sections(story, words, G, model="sonnet", effort="high"):
    lib_src = open(os.path.join(HERE, "lib.js")).read()
    jobs = {f"sec{k}": coder_prompt(story, k, words, G, lib_src) for k in range(len(story["sections"]))}

    def one(item):
        sid, p = item
        text, meta = call(p, model, effort)
        return sid, _code(text), meta, p

    with ThreadPoolExecutor(len(jobs)) as ex:
        res = list(ex.map(one, jobs.items()))
    return {sid: c for sid, c, _, _ in res}, {sid: m for sid, _, m, _ in res}, {sid: p for sid, _, _, p in res}


def repair(sid, code, problems, prompt, model="sonnet", effort="high"):
    p = (prompt + f"\n\nYOUR PREVIOUS CODE for this section:\n```js\n{code}\n```\n\nVALIDATOR REPORT (fix ALL of it, keep the design):\n"
         + "\n".join(f"- {x}" for x in problems) + "\nReturn the corrected full function body in one ```js block.")
    text, meta = call(p, model, effort)
    return _code(text), meta
