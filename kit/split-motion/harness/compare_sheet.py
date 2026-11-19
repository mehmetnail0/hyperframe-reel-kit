#!/usr/bin/env python3
"""Side-by-side sheet: N videos as columns, one row per timestamp (same timestamps for all).

usage: python3 -I compare_sheet.py OUT.jpg --every 3 --label A=a.mp4 --label B=b.mp4 ...
Rows are split into two halves placed next to each other so the sheet stays printable.
"""
import subprocess, sys

import cv2
import numpy as np

a = sys.argv[1:]
out = a[0]
every = float(a[a.index("--every") + 1]) if "--every" in a else 3.0
cols = [x.split("=", 1) for i, x in enumerate(a) if i and a[i - 1] == "--label"]
TW, TH = 180, 320


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


T = min(dur(p) for _, p in cols)
ts = [round(k * every + .5, 2) for k in range(int((T - .5) // every) + 1)]


def grab(p, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", p, "-frames:v", "1", "-vf", f"scale={TW}:{TH}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(TH, TW, 3) if len(raw) == TW * TH * 3 else np.zeros((TH, TW, 3), np.uint8)


half = (len(ts) + 1) // 2
gap, lab_w, head = 6, 64, 44
block_w = lab_w + len(cols) * (TW + gap)
W = 2 * block_w + 20
H = head + half * (TH + gap)
img = np.full((H, W, 3), 18, np.uint8)
for b in range(2):
    x0 = b * (block_w + 20)
    for c, (name, _) in enumerate(cols):
        cv2.putText(img, name, (x0 + lab_w + c * (TW + gap) + 4, 30), cv2.FONT_HERSHEY_SIMPLEX, .62, (80, 220, 255), 2)
for i, t in enumerate(ts):
    b, r = divmod(i, half)
    x0, y0 = b * (block_w + 20), head + r * (TH + gap)
    cv2.putText(img, f"{t:.1f}s", (x0 + 4, y0 + TH // 2), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
    for c, (_, p) in enumerate(cols):
        x = x0 + lab_w + c * (TW + gap)
        img[y0:y0 + TH, x:x + TW] = grab(p, t)
cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(out, img.shape, len(ts), "rows")
