#!/usr/bin/env python3
"""Automatic jump / stutter detector for rendered reels (QC gate).

usage: python3 -I jumps.py FINAL.mp4 [--beats data/beats.json] [--seams 451,911] [--panel-h 1370] [--json out.json]

Decodes EVERY frame of the motion-panel region (gray, 270 px wide) and looks for:
  repeat  — a frame identical to the previous one while motion is running on both sides
            (dropped/duplicated frame -> visible hitch)
  spike   — a one-frame outlier: |f[i]-f[i-1]| far above the local median AND f[i+1] goes
            back toward f[i-1] (a frame that 'pops' out of the motion: jump, flash, re-layout)
  step    — a sudden displacement inside a hold (diff spike with flat motion before and
            after, not at a planned cut): an element snapping / jumping position
  seam    — the frame-diff at each render-chunk boundary vs its neighbours
Expected discontinuities (beat/layout cuts, +-2 frames) are excluded.
Also reports the MOTION BUDGET: share of in-beat frames (outside entry/exit windows) that
carry low-level ambient motion (drift), the thing the new motion language keeps rare.
"""
import json, subprocess, sys

import numpy as np

FPS = 30


def frames(path, y0, y1, w=270):
    h = int(round((y1 - y0) * w / 1080 / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"crop=1080:{y1 - y0}:0:{y0},scale={w}:{h}:flags=area,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def analyse(path, beats=None, seams=(), panel_h=1370, cap_top=None, chunk_plan=None):
    """region = y 150 .. caption top (the seam caption swaps words on purpose and is excluded)."""
    y1 = (cap_top - 8) if cap_top else panel_h - 10
    a = frames(path, 150, y1)
    n, H, W = a.shape
    th, tw = H // 6, W // 6
    tiles = a[:, :th * 6, :tw * 6].reshape(n, 6, th, 6, tw)
    dt = np.r_[np.zeros((1, 36)), np.abs(np.diff(tiles, axis=0)).mean(axis=(2, 4)).reshape(n - 1, 36)]  # dt[i] = |f[i]-f[i-1]|
    d = dt.mean(axis=1)
    expected = np.zeros(n, bool)
    entering = np.zeros(n, bool)  # scene entrance (wipe/iris edges travel across tiles by design)
    hold = np.zeros(n, bool)
    split = np.zeros(n, bool)
    for b in beats or []:
        i0, i1 = int(round(b["t0"] * FPS)), int(round(b["t1"] * FPS))
        expected[max(0, i0 - 2):i0 + 3] = True
        expected[max(0, i1 - 13):i1 + 1] = True      # exit window
        entering[i0:i0 + int(.75 * FPS)] = True
        if b["layout"] != "speaker":
            split[i0:i1] = True
            hold[min(i1, i0 + int(1.2 * FPS)):max(i0, i1 - int(.5 * FPS))] = True
    issues = []
    for i in range(2, n - 1):
        if not split[i] or expected[i]:
            continue
        if d[i] < .02 and d[i - 1] > .35 and d[i + 1] > .35:
            issues.append(dict(kind="repeat", frame=i, t=round(i / FPS, 3)))
            continue
        k = int(np.argmax(dt[i]))
        c = dt[i, k]
        if c < 6:
            continue
        r, cc = divmod(k, 6)
        back = float(np.abs(tiles[i + 1, r, :, cc, :] - tiles[i - 1, r, :, cc, :]).mean())
        if back < .35 * c:
            issues.append(dict(kind="pop", frame=i, t=round(i / FPS, 3), tile=k, d=round(float(c), 1)))
        elif c > 12 and dt[i - 1, k] < c / 8 and dt[i + 1, k] < c / 8 and not entering[i]:
            issues.append(dict(kind="snap", frame=i, t=round(i / FPS, 3), tile=k, d=round(float(c), 1)))
    seam_rep = []
    for s_ in seams:
        if 2 < s_ < n - 3:
            loc = float(np.median(np.r_[d[s_ - 4:s_], d[s_ + 1:s_ + 5]]))
            rep = dict(frame=s_, t=round(s_ / FPS, 3), d=round(float(d[s_]), 3), local=round(loc, 3),
                       ratio=round(float(d[s_]) / max(.05, loc), 2), repeat=bool(d[s_] < .02 and loc > .3))
            seam_rep.append(rep)
            if rep["repeat"] or (rep["ratio"] > 4 and d[s_] > 1.0 and not expected[s_]):
                issues.append(dict(kind="seam", frame=s_, t=rep["t"], d=rep["d"], local=rep["local"]))
    amb = (d > .2) & hold
    budget = float(amb.sum() / max(1, hold.sum()))
    kinds = {}
    for x in issues:
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    if chunk_plan:  # which render chunk each issue is in (the QC loop re-renders those)
        bounds = np.cumsum([0] + [c[2] for c in chunk_plan])
        for x in issues:
            x["chunk"] = int(np.searchsorted(bounds, x["frame"], side="right") - 1)
    return dict(frames=n, flagged=len(issues), by_kind=kinds, issues=issues[:120], seams=seam_rep,
                ambient_motion_share=round(budget, 3), hold_frames=int(hold.sum()))


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, dflt=None: a[a.index(k) + 1] if k in a else dflt  # noqa: E731
    beats = json.load(open(opt("--beats")))["beats"] if opt("--beats") else None
    seams = [int(x) for x in opt("--seams", "").split(",") if x]
    r = analyse(a[0], beats, seams, int(opt("--panel-h", "1370")), int(opt("--cap-top")) if opt("--cap-top") else None)
    if opt("--json"):
        json.dump(r, open(opt("--json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in r.items() if k != "issues"}, indent=1))
    for x in r["issues"][:40]:
        print(x)


def card_repeats(path, card_y, beats):
    """duplicated frames in the speaker card (base video VFR / fps-conversion duplicates)."""
    a = frames(path, card_y + 10, 1890, w=180)
    d = np.r_[9, np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))]
    split = np.zeros(len(d), bool)
    for b in beats or []:
        if b["layout"] != "speaker":
            split[int(round(b["t0"] * FPS)) + 2:int(round(b["t1"] * FPS)) - 2] = True
    rep = [i for i in range(1, len(d) - 1) if split[i] and d[i] < .03 and d[i - 1] > .3 and d[i + 1] > .3]
    return dict(card_repeats=len(rep), at=[round(i / FPS, 2) for i in rep][:20])
