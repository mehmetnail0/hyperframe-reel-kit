#!/usr/bin/env python3
"""split-motion HARNESS: raw talking-head clip in -> finished reel out (target 5-8 min wall incl. render).

usage:
  python3 -I kit/split-motion/harness/run.py RAW.mp4 REEL_DIR --sfx-lib "LIB_DIR" [--topic "..."]
         [--model claude|local|anthropic|openai|gemini] [--seed N] [--len 55-75] [--theme dark|light]
         [--music BED.wav] [--chunks N] [--out FINAL.mp4] [--plan plan.json]   (--plan = reuse a plan, skip the model)

Pipeline (each step timed into REEL_DIR/build/timings.json):
  1 ingest     ║ transcribe (faster-whisper) ║ vision (1 decode: shots+faces+sheet) ║ energy        — parallel
  2 plan       ONE model call -> plan.json (validated + repaired in code), then the novelty pass vs memory
  3 cut        EDL from word ranges (energy-dip snapped) + words on the cut timeline + beat times
  4 build      ║ base video (parallel ffmpeg sub-segments) ║ speech + SFX engine + mix ║ HTML compile + DOM QC fit — parallel
  5 render     N frame-exact chunks rendered concurrently, cropped as they finish, lossless concat + audio mux
  6 qc         loudness, motion, sheet; issues -> report (auto-fixes happen in 4: DOM fit, SFX rules, loudness)
  7 memory     the reel's motion/SFX fingerprint -> kit/split-motion/memory/history.json (next reel avoids it)
"""
import json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(KIT))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "sfx"))
import ingest, planner, novelty, cut, scenes, render, qc  # noqa: E402
import engine as sfx_engine  # noqa: E402

MEMORY = os.path.join(KIT, "memory", "history.json")
ASSET_SRC = os.path.join(REPO, "split-motion-dai")


class Clock:
    def __init__(self, path):
        self.t0 = time.time()
        self.steps = []
        self.path = path

    def step(self, name, secs, **kw):
        kw = {(f"x_{k}" if k in ("s", "step", "at") else k): v for k, v in kw.items()}
        self.steps.append(dict(step=name, s=round(secs, 1), at=round(time.time() - self.t0, 1), **kw))
        print(f"[{time.time() - self.t0:6.1f}s] {name}: {secs:.1f}s {json.dumps(kw)[:300] if kw else ''}", flush=True)
        json.dump(dict(total_s=round(time.time() - self.t0, 1), steps=self.steps), open(self.path, "w"), indent=1)


def stage_project(reel):
    """reel folder skeleton (fonts, gsap, three.js, package.json) — copied once, cached."""
    for d in ("assets/fonts", "assets/vendor", "renders", "build", "data"):
        os.makedirs(os.path.join(reel, d), exist_ok=True)
    for f in ("ProductSans-Regular.woff", "ProductSans-Bold.woff", "ProductSans-Black.woff", "InstrumentSerif-Italic.woff2", "InstrumentSerif-OFL.txt"):
        src = os.path.join(ASSET_SRC, "assets", "fonts", f)
        if not os.path.exists(src):
            src = os.path.join(ASSET_SRC, "demo-3d", "assets", "fonts", f)
        dst = os.path.join(reel, "assets", "fonts", f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy(src, dst)
    if not os.path.exists(os.path.join(reel, "assets", "vendor", "gsap.min.js")):
        shutil.copy(os.path.join(ASSET_SRC, "assets", "vendor", "gsap.min.js"), os.path.join(reel, "assets", "vendor", "gsap.min.js"))
    if not os.path.exists(os.path.join(reel, "assets", "vendor", "three")):
        shutil.copytree(os.path.join(ASSET_SRC, "demo-3d", "assets", "vendor", "three"), os.path.join(reel, "assets", "vendor", "three"))
    for f in ("package.json", "hyperframes.json"):
        if not os.path.exists(os.path.join(reel, f)):
            shutil.copy(os.path.join(ASSET_SRC, f), os.path.join(reel, f))


def main(argv):
    a = argv[1:]
    raw, reel = os.path.abspath(a[0]), os.path.abspath(a[1])
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d  # noqa: E731
    lib = opt("--sfx-lib")
    seed = int(opt("--seed", "7"))
    lo, hi = (float(x) for x in opt("--len", "55-75").split("-"))
    model = opt("--model")
    theme = opt("--theme", "dark")
    out = os.path.abspath(opt("--out", os.path.join(reel, "renders", "FINAL.mp4")))
    nchunks = int(opt("--chunks", str(os.cpu_count() or 4)))
    stage_project(reel)
    work = os.path.join(reel, "build")
    clk = Clock(os.path.join(work, "timings.json"))
    # warm caches in the background: npx resolution of hyperframes + Chrome (first render otherwise pays it)
    warm = subprocess.Popen(render.HF + ["--version"], cwd=reel, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 1 ingest || 2 plan: the model call starts as soon as the transcript exists and overlaps the
    #   (slow, 4K) vision decode; shots are only needed later by the cut.
    t = time.time()
    st = os.stat(raw)
    key = f"{os.path.basename(raw)}|{st.st_size}|{int(st.st_mtime)}|{opt('--whisper', 'small.en')}"
    kp = os.path.join(work, "ingest.key")
    cached = os.path.exists(kp) and open(kp).read() == key and "--no-cache" not in a and \
        all(os.path.exists(os.path.join(work, f)) for f in ("words.json", "shots.json", "energy.npy"))
    mem = novelty.load(MEMORY)
    from concurrent.futures import ProcessPoolExecutor
    ex = ProcessPoolExecutor(3)
    fv = fe = None
    if cached:
        clk.step("1 ingest (cache hit)", time.time() - t, key=key)
    else:
        nthr = max(1, (os.cpu_count() or 4) - 2)
        ft = ex.submit(ingest.transcribe, raw, work, opt("--whisper", "small.en"), "en", nthr)
        fv = ex.submit(ingest.vision, raw, work)
        fe = ex.submit(ingest.energy, raw, work)
        tr = ft.result()
        clk.step("1a transcribe", time.time() - t, **tr)
    W = json.load(open(os.path.join(work, "words.json")))
    words, segs = W["words"], W["segments"]
    t2 = time.time()
    shots_hint = json.load(open(os.path.join(work, "shots.json"))) if cached else {"shots": []}
    if opt("--plan"):
        plan = json.load(open(opt("--plan")))
        plan, fixes = planner.validate(plan, words)
        plan["seed"] = seed
        pmeta = dict(adapter="reuse", fixes=fixes)
    else:
        plan, pmeta = planner.make_plan(words, segs, shots_hint, mem, dict(min_len=lo, max_len=hi, seed=seed, topic=opt("--topic"), theme=theme), model)
    clk.step("2 plan (model call, overlaps vision)", time.time() - t2, model=pmeta)
    if fv:
        vr, er = fv.result(), fe.result()
        clk.step("1b vision+energy (finished)", time.time() - t, vision=vr, energy=er)
        open(kp, "w").write(key)
    ex.shutdown()
    shots = json.load(open(os.path.join(work, "shots.json")))
    import numpy as np
    en = np.load(os.path.join(work, "energy.npy"))
    t = time.time()
    plan, nov = novelty.apply(plan, mem, seed)
    json.dump(plan, open(os.path.join(reel, "data", "plan.json"), "w"), indent=1, ensure_ascii=False)
    clk.step("2b novelty pass", time.time() - t, changes=nov)

    # 3 cut (fast, no video)
    t = time.time()
    E, total_speech = cut.edl(plan, words, en)
    cw = cut.remap_words(words, E)
    srcmap = {w["src"]: k for k, w in enumerate(cw)}
    for b in plan["beats"]:  # word indices -> cut timeline indices
        b["w0"] = srcmap.get(b["w0"], min(srcmap.values(), key=lambda k: abs(cw[k]["src"] - b["w0"])))
        sc = b.get("scene") or {}
        if sc.get("at"):
            sc["at"] = [srcmap.get(i) for i in sc["at"]]
    plan["emph"] = [srcmap[i] for i in plan.get("emph", []) if i in srcmap]
    tail = .8
    total = round(total_speech + tail, 3)
    bt = scenes.beat_times(plan, cw, total)
    # a full-screen speaker beat must show a FACE: if most of it sits on a faceless camera
    # angle (wide/B-cam), it becomes a split beat with a quote of its own words
    def faceless_share(a_, b_):
        n_, bad = 0, 0
        for x in np.arange(a_, b_, .2):
            src_t = next((sg["i"] + x - sg["s"] for sg in E if sg["s"] <= x < sg["s"] + sg["o"] - sg["i"]), None)
            if src_t is None:
                continue
            sh = next((q for q in shots["shots"] if q["t0"] <= src_t < q["t1"]), None)
            n_ += 1
            bad += 1 if (sh is None or not sh["face"]) else 0
        return bad / max(1, n_)
    swapped = []
    for (a_, b_), b in zip(bt, plan["beats"]):
        if b.get("layout") == "speaker" and faceless_share(a_, b_) > .3:
            ws = [w["w"] for w in cw if a_ <= w["t"] < b_][:5]
            b["layout"] = "split"
            b["scene"] = {"type": "quote", "text": " ".join(ws[:-1]) + (f" *{ws[-1]}*" if ws else ""), "enter": "focus", "exit": "blur", "camera": "push"}
            swapped.append(round(a_, 2))
    lays = [(x, y, b.get("layout", "split")) for (x, y), b in zip(bt, plan["beats"])]
    json.dump(dict(segments=E, total=total), open(os.path.join(reel, "data", "edl.json"), "w"), indent=1)
    json.dump(cw, open(os.path.join(reel, "data", "words.json"), "w"), indent=0)
    clk.step("3 cut (EDL + remap)", time.time() - t, segments=len(E), speech_s=total_speech, faceless_speaker_beats_to_split=swapped)

    # speaker caption height: below the chin of the main face in the 9:16 crop
    faces = [s["face"] for s in shots["shots"] if s["face"]]
    face_cap_y = 1180
    if faces:
        f = sorted(faces, key=lambda f: -f["size"])[len(faces) // 2]
        w_, h_, x_, y_ = cut.crop_for(shots["src"], f, "speaker")
        chin = (f["cy"] + .75 * f["size"] - y_) / h_ * 1920
        face_cap_y = int(min(1460, max(1080, chin + 40)))

    # 4 build (parallel)
    t = time.time()
    ctx = dict(seed=seed, face_cap_y=face_cap_y, audio="assets/mix.wav")
    timing = {}

    def job_video():
        a0 = time.time()
        n = cut.base_video(raw, E, shots, lays, os.path.join(reel, "assets", "video.mp4"), plan.get("theme", theme), tail=tail)
        timing["base_video"] = (round(time.time() - a0, 1), n)

    def job_audio():
        a0 = time.time()
        sp = os.path.join(work, "speech.wav")
        cut.speech(raw, E, sp)
        timing["speech"] = round(time.time() - a0, 1)
        return sp

    def job_html():
        a0 = time.time()
        html, cues, mb, caps = scenes.compile_reel(plan, cw, total, ctx)
        ip = os.path.join(reel, "index.html")
        open(ip, "w").write(html)
        fit, notes = qc.dom_fit(ip, mb, work)
        if fit:
            ctx["fit"] = fit
            html, cues, mb, caps = scenes.compile_reel(plan, cw, total, ctx)
            open(ip, "w").write(html)
        timing["html"] = (round(time.time() - a0, 1), len(fit), notes[:12])
        return cues, mb, caps

    with ThreadPoolExecutor(3) as ex:
        fv, fa, fh = ex.submit(job_video), ex.submit(job_audio), ex.submit(job_html)
        sp = fa.result()
        cues, mb, caps = fh.result()
        # SFX (needs the cues from the compile): engine with anti-repeat, then the mix
        a0 = time.time()
        pal = json.load(open(os.path.join(KIT, "sfx", "palette.json")))
        last = (mem.get("recent") or [{}])[-1]
        evs, budget, ncues = sfx_engine.plan(pal, cues, seed=seed, per_min=float(opt("--sfx-per-min", "16")), total=total,
                                             memory={"sfx_first": last.get("sfx_first", {})})
        viol = sfx_engine.check(evs)
        mp = os.path.join(reel, "data", "sfx-map.json")
        json.dump(sfx_engine.to_map(pal, evs, "nail-sfx/sound effects /"), open(mp, "w"), indent=1, ensure_ascii=False)
        if lib:
            subprocess.run([sys.executable, "-I", os.path.join(KIT, "sfx_mix.py"), "mix", mp, lib, sp,
                            os.path.join(reel, "assets", "mix.wav"), f"{total:.3f}"] + (["--music", opt("--music")] if opt("--music") else []),
                           check=True)
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", sp, "-af", f"apad=whole_dur={total:.3f},loudnorm=I=-14:TP=-1.5",
                            os.path.join(reel, "assets", "mix.wav")], check=True)
        timing["sfx_mix"] = (round(time.time() - a0, 1), len(evs), budget, ncues, viol)
        fv.result()
    json.dump(dict(beats=mb, captions=caps), open(os.path.join(reel, "data", "beats.json"), "w"), indent=1)
    clk.step("4 build (video || audio+sfx || html+fit)", time.time() - t, **{k: v for k, v in timing.items()})

    # 5 render
    warm.wait()
    t = time.time()
    rctx = dict(ctx, video_mode="speaker_only")
    split_iv = [(b["t0"], b["t1"]) for b in mb if b["layout"] == "split"]
    rr = render.render(reel, lambda off, dur: scenes.compile_reel(plan, cw, total, rctx, chunk=(off, dur))[0],
                       total, os.path.join(reel, "assets", "mix.wav"), out, n=nchunks, workers=int(opt("--workers", "1")),
                       card_from=os.path.join(reel, "assets", "video.mp4"), split_iv=split_iv,
                       cost=lambda t: next((3.0 if b["type"] == "hero3d" else (1.6 if b["layout"] == "speaker" else 1.0)
                                            for b in mb if b["t0"] <= t < b["t1"]), 1.0))
    clk.step("5 render (chunked, parallel)", time.time() - t, **rr)

    # 6 qc
    t = time.time()
    rep = qc.final(out, mb, None, os.path.join(reel, "renders"))
    os.replace(os.path.join(reel, "renders", "sheet-v.jpg"), os.path.splitext(out)[0] + "-sheet.jpg")
    clk.step("6 qc", time.time() - t, **rep)

    # 7 memory
    novelty.record(MEMORY, plan, os.path.basename(reel) + ":" + os.path.basename(out), evs, time.strftime("%Y-%m-%d"))
    clk.step("7 memory", 0.0, reel=os.path.basename(out))
    print(f"DONE {out}  total {time.time() - clk.t0:.1f}s")


if __name__ == "__main__":
    os.setpgrp()  # own process group: a crash must not leave ingest/render workers running
    try:
        main(sys.argv)
    except BaseException:
        import signal, traceback
        traceback.print_exc()
        sys.stdout.flush()
        os.killpg(0, signal.SIGKILL)
