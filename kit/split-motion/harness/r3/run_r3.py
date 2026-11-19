#!/usr/bin/env python3
"""split-motion ROUND 3 harness: director (Claude Opus) -> parallel scene coders (Claude) -> validate/repair -> render.

usage: python3 -I kit/split-motion/harness/r3/run_r3.py RAW.mp4 REEL_DIR --sfx-lib LIB --coder sonnet|opus
        [--storyboard data/storyboard.json] [--seed N] [--len 55-72] [--topic ".."] [--chunks N] [--out FILE] [--speaker-h 940]
Steps (timed into REEL_DIR/build/timings.json, tokens per Claude call included):
  1 ingest || 2 director   3 cut   4 coders (parallel per section) || base video || speech
  4b compose + validate + repair (max 2 loops)   4c SFX   5 chunked render   5b jumps QC   5c density QC   6 loudness/sheet
"""
import json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
HARN = os.path.dirname(HERE)
KIT = os.path.dirname(HARN)
sys.path[:0] = [HERE, HARN, os.path.join(KIT, "sfx")]
import ingest, cut, scenes, render, qc, jumps, planner  # noqa: E402
import engine as sfx_engine  # noqa: E402
import compose, claude_stage, density  # noqa: E402
from run import Clock, stage_project  # noqa: E402


def to_cut(story, srcmap, cw):
    near = lambda i: srcmap.get(i, min(srcmap.values(), key=lambda k: abs(cw[k]["src"] - i)))  # noqa: E731
    for s in story["sections"]:
        s["w0"], s["w1"] = near(s["w0"]), near(s["w1"])
        for e in s.get("events", []):
            if e.get("w") is not None:
                e["w"] = near(e["w"])
    story["speaker"] = [[near(a), near(b)] for a, b in story.get("speaker", [])]
    story["emph"] = [srcmap[i] for i in story.get("emph", []) if i in srcmap]
    secs = sorted(story["sections"], key=lambda s: s["w0"])
    secs[0]["w0"] = 0
    story["sections"] = [s for i, s in enumerate(secs) if i == 0 or s["w0"] > secs[i - 1]["w0"]]
    return story


def split_beats(st, spk, total):
    """non-overlapping beats for QC: sections minus speaker runs."""
    out = []
    for k, (a, b) in enumerate(st):
        cur = a
        for x, y in sorted(spk):
            if y <= cur or x >= b:
                continue
            if x > cur:
                out.append(dict(sid=f"sec{k}", t0=cur, t1=x, layout="split", type="r3"))
            cur = max(cur, y)
        if cur < b:
            out.append(dict(sid=f"sec{k}", t0=cur, t1=b, layout="split", type="r3"))
    for x, y in spk:
        out.append(dict(sid=None, t0=x, t1=y, layout="speaker", type=None))
    return sorted(out, key=lambda d: d["t0"])


def validate(reel, html, st, work, spk=()):
    src = html
    import re
    src = re.sub(r'<video[^>]*></video>', '', src)
    src = re.sub(r'<audio[^>]*></audio>', '', src)
    qh = os.path.join(reel, "_qc.html")
    open(qh, "w").write(src)
    sj = os.path.join(work, "r3_secs.json")
    json.dump([dict(sid=f"sec{k}", t0=a, t1=b, skip=[list(x) for x in spk]) for k, (a, b) in enumerate(st)], open(sj, "w"))
    oj = os.path.join(work, "r3_validate.json")
    env = dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
    r = subprocess.run(["node", os.path.join(HERE, "validate.js"), qh, sj, oj], capture_output=True, text=True, env=env)
    os.remove(qh)
    if r.returncode != 0:
        return {"errors": ["validator crashed: " + r.stderr[-300:]], "sections": [], "r3err": []}
    return json.load(open(oj))


def problems_by_section(rep):
    probs = {}
    for e in rep.get("r3err", []):
        sid = e.split(":")[0]
        probs.setdefault(sid, []).append("runtime error: " + e)
    for e in rep.get("errors", []):
        probs.setdefault("_all", []).append(e)
    for s in rep.get("sections", []):
        p = []
        if s["share_ge3"] < .95:
            p.append(f"only {s['share_ge3']:.0%} of the section time has >= 3 visible elements (need >= 95 %); mean {s['mean_elements']:.1f}")
        if s["lonely_share"] > .05:
            p.append(f"{s['lonely_share']:.0%} of the time a single lonely object (need <= 5 %)")
        for o in s["overflow"]:
            p.append(f"element outside the allowed stage: {o}")
        if s["device_overflow"]:
            p.append(f"content leaves its phone/device screen at t={s['device_overflow']}")
        if p:
            probs.setdefault(s["sid"], []).extend(p)
    return probs


def main(a):
    raw, reel = os.path.abspath(a[0]), os.path.abspath(a[1])
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d  # noqa: E731
    lib, coder = opt("--sfx-lib"), opt("--coder", "sonnet")
    seed = int(opt("--seed", "41"))
    lo, hi = (float(x) for x in opt("--len", "55-72").split("-"))
    out = os.path.abspath(opt("--out", os.path.join(reel, "renders", f"r3-{coder}.mp4")))
    stage_project(reel)
    work = os.path.join(reel, "build")
    clk = Clock(os.path.join(work, "timings.json"))
    tokens = []
    G = scenes.geometry(float(opt("--speaker-h", "940")))
    cut.set_geometry(G)
    qc.set_geometry(G)
    warm = subprocess.Popen(render.HF + ["--version"], cwd=reel, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 1 ingest || 2 director
    t = time.time()
    st_ = os.stat(raw)
    key = f"{os.path.basename(raw)}|{st_.st_size}|{int(st_.st_mtime)}|small.en"
    kp = os.path.join(work, "ingest.key")
    cached = os.path.exists(kp) and open(kp).read() == key and all(os.path.exists(os.path.join(work, f)) for f in ("words.json", "shots.json", "energy.npy"))
    ex = ProcessPoolExecutor(3)
    fv = None
    if not cached:
        ft = ex.submit(ingest.transcribe, raw, work, "small.en", "en", 2)
        fv, fe = ex.submit(ingest.vision, raw, work), ex.submit(ingest.energy, raw, work)
        clk.step("1a transcribe", time.time() - t, **ft.result())
    else:
        clk.step("1 ingest (cache hit)", time.time() - t)
    Wj = json.load(open(os.path.join(work, "words.json")))
    words, segs = Wj["words"], Wj["segments"]
    t2 = time.time()
    if opt("--storyboard"):
        story = json.load(open(opt("--storyboard")))
        clk.step("2 director (reused storyboard)", time.time() - t2, file=opt("--storyboard"))
    else:
        story, meta, _ = claude_stage.director(words, segs, dict(min_len=lo, max_len=hi, topic=opt("--topic"), panel_h=G["panel_h"]))
        tokens.append(dict(stage="director", **meta))
        os.makedirs(os.path.join(reel, "data"), exist_ok=True)
        json.dump(story, open(os.path.join(reel, "data", "storyboard.json"), "w"), indent=1, ensure_ascii=False)
        clk.step("2 director (claude, overlaps vision)", time.time() - t2, **meta)
    if fv:
        clk.step("1b vision+energy (finished)", time.time() - t, vision=fv.result(), energy=fe.result())
        open(kp, "w").write(key)
    ex.shutdown()
    shots = json.load(open(os.path.join(work, "shots.json")))
    import numpy as np
    en = np.load(os.path.join(work, "energy.npy"))

    # 3 cut
    t = time.time()
    plan_like = {"keep": story.get("keep") or [[0, len(words) - 1]]}
    E, speech_s = cut.edl(plan_like, words, en)
    cw = cut.remap_words(words, E)
    srcmap = {w["src"]: k for k, w in enumerate(cw)}
    story = to_cut(json.loads(json.dumps(story)), srcmap, cw)
    total = round(speech_s + .8, 3)
    st = compose.section_times(story, cw, total)
    for s, (a_, b_) in zip(story["sections"], st):
        s["_t0"], s["_t1"] = a_, b_
    spk = compose.speaker_runs(story, cw, total)
    lays = [(x, y, "speaker") for x, y in spk]
    full = []
    cur = 0.0
    for x, y in sorted(lays):
        if x > cur:
            full.append((cur, x, "split"))
        full.append((x, y, "speaker"))
        cur = y
    if cur < total:
        full.append((cur, total, "split"))
    json.dump(dict(segments=E, total=total), open(os.path.join(reel, "data", "edl.json"), "w"), indent=1)
    json.dump(cw, open(os.path.join(reel, "data", "words.json"), "w"), indent=0)
    json.dump(story, open(os.path.join(reel, "data", "storyboard_cut.json"), "w"), indent=1, ensure_ascii=False)
    clk.step("3 cut", time.time() - t, sections=len(st), speaker_runs=len(spk), speech_s=speech_s)

    faces = [s["face"] for s in shots["shots"] if s["face"]]
    face_cap_y = 1180
    if faces:
        f = sorted(faces, key=lambda f: -f["size"])[len(faces) // 2]
        w_, h_, x_, y_ = cut.crop_for(shots["src"], f, "speaker")
        face_cap_y = int(min(1460, max(1080, (f["cy"] + .75 * f["size"] - y_) / h_ * 1920 + 40)))
    ctx = dict(geom=G, face_cap_y=face_cap_y, audio="assets/mix.wav")

    # 4 coders || base video || speech
    t = time.time()
    timing = {}

    def job_video():
        a0 = time.time()
        cut.base_video(raw, E, shots, full, os.path.join(reel, "assets", "video.mp4"), "dark", tail=.8, geom=G)
        timing["base_video"] = round(time.time() - a0, 1)

    def job_speech():
        a0 = time.time()
        cut.speech(raw, E, os.path.join(work, "speech.wav"))
        timing["speech"] = round(time.time() - a0, 1)

    with ThreadPoolExecutor(3) as tp:
        fvid, fsp = tp.submit(job_video), tp.submit(job_speech)
        a0 = time.time()
        codes, metas, prompts = claude_stage.code_sections(story, cw, G, coder)
        for sid, m in metas.items():
            tokens.append(dict(stage=f"coder {sid}", **m))
        timing["coders_parallel"] = dict(s=round(time.time() - a0, 1), sections=len(codes), per_section_s={k: v["s"] for k, v in metas.items()})
        clk.step("4 scene coders (parallel)", time.time() - a0, coder=coder, per_section={k: dict(s=v["s"], out_tok=v["out_tok"]) for k, v in metas.items()})
        # 4b compose + validate + repair
        a1 = time.time()
        loops = []
        for loop in range(3):
            html, cues, beats, caps, st, spk = compose.compose(story, codes, cw, total, ctx)
            rep = validate(reel, html, st, work, spk)
            probs = problems_by_section(rep)
            loops.append(dict(loop=loop, problems={k: len(v) for k, v in probs.items()},
                              share_ge3=[round(s["share_ge3"], 2) for s in rep.get("sections", [])]))
            fix = {k: v for k, v in probs.items() if k.startswith("sec")}
            if not fix or loop == 2:
                break
            def rp(item):
                sid, pr = item
                c, m = claude_stage.repair(sid, codes[sid], pr, prompts[sid], coder)
                return sid, c, m
            with ThreadPoolExecutor(len(fix)) as tp2:
                for sid, c, m in tp2.map(rp, fix.items()):
                    codes[sid] = c
                    tokens.append(dict(stage=f"repair {sid} loop {loop + 1}", **m))
        open(os.path.join(reel, "index.html"), "w").write(html)
        json.dump(codes, open(os.path.join(reel, "data", f"codes-{coder}.json"), "w"), indent=1)
        clk.step("4b compose + validate + repair", time.time() - a1, loops=loops, final=rep.get("sections"), errors=rep.get("errors", [])[:5])
        # 4c SFX
        a2 = time.time()
        pal = json.load(open(os.path.join(KIT, "sfx", "palette.json")))
        evs, budget, ncues = sfx_engine.plan(pal, cues, seed=seed, per_min=16, total=total)
        mp = os.path.join(reel, "data", "sfx-map.json")
        json.dump(sfx_engine.to_map(pal, evs, "nail-sfx/sound effects /"), open(mp, "w"), indent=1, ensure_ascii=False)
        subprocess.run([sys.executable, "-I", os.path.join(KIT, "sfx_mix.py"), "mix", mp, lib, os.path.join(work, "speech.wav"),
                        os.path.join(reel, "assets", "mix.wav"), f"{total:.3f}"], check=True) if lib else None
        timing["sfx"] = dict(s=round(time.time() - a2, 1), events=len(evs), violations=sfx_engine.check(evs))
        fvid.result(); fsp.result()
    clk.step("4 build total (coders || video || speech)", time.time() - t, **timing)

    # 5 render
    warm.wait()
    t = time.time()
    qbeats = split_beats(st, spk, total)
    json.dump(dict(beats=qbeats, sections=st, speaker=spk), open(os.path.join(reel, "data", "beats.json"), "w"), indent=1)
    split_iv = [(b["t0"], b["t1"]) for b in qbeats if b["layout"] == "split"]
    mk = lambda off, dur: compose.compose(story, codes, cw, total, ctx, chunk=(off, dur))[0]  # noqa: E731
    cost = lambda x: 1.6 if any(p <= x < q for p, q in spk) else 1.0  # noqa: E731
    rargs = dict(n=int(opt("--chunks", "4")), workers=1, card_from=os.path.join(reel, "assets", "video.mp4"), split_iv=split_iv,
                 band_y=G["panel_h"], keep=True)
    rr = render.render(reel, mk, total, os.path.join(reel, "assets", "mix.wav"), out, cost=cost, **rargs)
    clk.step("5 render (chunked)", time.time() - t, **{k: v for k, v in rr.items() if k != "chunk_plan"})

    # 5b jumps (+ chunk re-render loop for render-side glitches)
    t = time.time()
    jr = jumps.analyse(out, qbeats, rr["seams"], G["panel_h"], G["cap_top"], rr["chunk_plan"])
    hist = [dict(flagged=jr["flagged"], by_kind=jr["by_kind"])]
    for _ in range(2):
        bad = sorted({x["chunk"] for x in jr["issues"] if x["kind"] in ("repeat", "seam", "pop")})
        if not bad:
            break
        before = {(x["kind"], x["frame"]) for x in jr["issues"]}
        render.render(reel, mk, total, os.path.join(reel, "assets", "mix.wav"), out, chunks=rr["chunk_plan"], only=bad, **rargs)
        jr = jumps.analyse(out, qbeats, rr["seams"], G["panel_h"], G["cap_top"], rr["chunk_plan"])
        hist.append(dict(rerendered=bad, flagged=jr["flagged"]))
        if {(x["kind"], x["frame"]) for x in jr["issues"]} == before:
            hist[-1]["verdict"] = "deterministic (composition)"
            break
    render.cleanup(reel)
    clk.step("5b jump QC", time.time() - t, loops=hist, issues=jr["issues"][:8])

    # 5c density QC
    t = time.time()
    ve = density.video_events(out, split_iv, G["cap_top"])
    dv = density.verdict(ve, rep, jr)
    json.dump(dict(density=dv, video_events=ve, dom=rep, jumps=jr), open(os.path.join(work, "qc_r3.json"), "w"), indent=1)
    clk.step("5c density QC", time.time() - t, **dv)

    # 6 loudness + sheet
    t = time.time()
    I, tp = qc.loudness(out)
    qc.sheet(out, os.path.splitext(out)[0] + "-sheet.jpg")
    tot_tok = dict(in_tok=sum(x["in_tok"] for x in tokens), out_tok=sum(x["out_tok"] for x in tokens),
                   cache_read=sum(x["cache_read"] for x in tokens), cache_write=sum(x["cache_write"] for x in tokens),
                   cost_usd=round(sum(x["cost_usd"] or 0 for x in tokens), 3), calls=len(tokens))
    json.dump(tokens, open(os.path.join(work, "tokens.json"), "w"), indent=1)
    clk.step("6 loudness + sheet", time.time() - t, lufs=I, true_peak=tp, claude_tokens=tot_tok)
    print(f"DONE {out} total {time.time() - clk.t0:.1f}s density={dv}")


if __name__ == "__main__":
    os.setpgrp()
    try:
        main(sys.argv[1:])
    except BaseException:
        import signal, traceback
        traceback.print_exc()
        sys.stdout.flush()
        os.killpg(0, signal.SIGKILL)
