#!/usr/bin/env python3
"""Motion QC for a split-motion render (pure Python, ffmpeg for decoding).

usage: python3 -I scripts/qc_motion.py VIDEO.mp4 [--panel-h 1150]

Samples the TOP PANEL (y 0..panel_h; full frame during punch-ins) at 10 fps,
downscaled to 108 px wide, and reports:
  * static runs   : stretches where consecutive frames differ by < 0.6/255 (mean abs)
  * major changes : frames where the panel changes by > 6/255 (object in/out, cut,
                    chapter fly-in, punch-in) and the longest gap between them.
Pass criteria for the style: no static run > 3.0 s AND no gap between major
changes > 3.0 s.
"""
import subprocess, sys

VID = sys.argv[1]
PH = int(sys.argv[sys.argv.index("--panel-h") + 1]) if "--panel-h" in sys.argv else 1150
FPS, W = 10, 108
H = round(PH * W / 1080)
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VID, "-vf",
                      f"fps={FPS},crop=1080:{PH}:0:0,scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                     capture_output=True, check=True).stdout
n = len(raw) // (W * H)
frames = [raw[i * W * H:(i + 1) * W * H] for i in range(n)]
diffs = [0.0]
for a, b in zip(frames, frames[1:]):
    diffs.append(sum(abs(x - y) for x, y in zip(a, b)) / (W * H))

STATIC, MAJOR = 0.6, 6.0
runs, cur = [], 0
for i, d in enumerate(diffs):
    if d < STATIC:
        cur += 1
    else:
        if cur:
            runs.append((i - cur, cur))
        cur = 0
if cur:
    runs.append((n - cur, cur))
long_static = [(s / FPS, l / FPS) for s, l in runs if l / FPS > 3.0]
majors = [i / FPS for i, d in enumerate(diffs) if d > MAJOR]
gaps, prev = [], 0.0
for t in majors + [n / FPS]:
    gaps.append((prev, t - prev)); prev = t
gaps.sort(key=lambda g: -g[1])
print(f"duration {n / FPS:.1f}s  frames {n}")
print(f"longest static run: {max([l for _, l in runs], default=0) / FPS:.1f}s; static runs > 3 s: {len(long_static)} {long_static}")
print(f"major panel changes: {len(majors)} (~1 per {n / FPS / max(1, len(majors)):.2f}s)")
print("longest gaps between major changes:", ", ".join(f"{g:.1f}s@{s:.1f}" for s, g in gaps[:6]))
print(f"seconds with no motion change > 3 s: {sum(l for _, l in long_static):.1f}")
