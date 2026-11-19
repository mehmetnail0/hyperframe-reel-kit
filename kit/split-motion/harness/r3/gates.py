#!/usr/bin/env python3
"""Frame gates (owner rules, fail the render):
  bg_gate(video, beats, G)    no glow / slab / dust in the panel background, on 5 split frames:
       * particles: small isolated bright dots on the dark background (connected components 3-80 px,
         >= 22 levels above the local median) — more than 4 per frame fails
       * blob: smooth raised background (Gaussian-blurred luma 14-90 with a gentle non-zero gradient and
         no texture: local std < 3) — a glowing slab/halo; area > 1.2 % of the panel fails.
         Flat card fills are excluded (zero gradient), text/edges are excluded (texture).
  geom_gate(video, beats, G)  flush geometry on 5 split frames: the seam rows between panel and card, the
       margins beside the card and the pixels just outside each rounded corner must all equal the panel
       background (+-3 levels), and the card must start exactly at card_x / card_y (no sliver, no gap)."""
import subprocess
import cv2
import numpy as np


def frame(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3).astype(np.int16)


def times(beats, n=5):
    sp = [b for b in beats if b["layout"] == "split" and b["t1"] - b["t0"] > 1.6]
    ts = [(b["t0"] + b["t1"]) / 2 for b in sp]
    if len(ts) <= n:
        return ts
    return [ts[int(i * (len(ts) - 1) / (n - 1))] for i in range(n)]


def bg_gate(video, beats, G):
    rep = []
    for t in times(beats):
        f = frame(video, t)
        y = f[150:G["cap_top"] - 10, :, :].mean(axis=2).astype(np.float32)
        med = cv2.medianBlur(np.clip(y, 0, 255).astype(np.uint8), 31).astype(np.float32)
        hot = ((y - med) > 22) & (med < 40)
        n, lab, st, _ = cv2.connectedComponentsWithStats(hot.astype(np.uint8), 8)
        # a particle floats in EMPTY dark space: its 61x61 neighbourhood (minus itself) is background-dark and has
        # no other bright structure (text glyphs / UI dots sit on cards or next to other strokes)
        allhot = (y - med) > 22
        near = cv2.blur(allhot.astype(np.float32), (61, 61))
        dark = cv2.blur(y, (61, 61))
        cen = lambda i: (int(st[i, 1] + st[i, 3] / 2), int(st[i, 0] + st[i, 2] / 2))  # noqa: E731
        dots = 0
        for i in range(1, n):
            if 3 <= st[i, 4] <= 80 and max(st[i, 2], st[i, 3]) <= 12:
                r_, c_ = cen(i)
                if dark[r_, c_] < 26 and near[r_, c_] * 3721 - st[i, 4] < 6:
                    dots += 1
        g = cv2.GaussianBlur(y, (0, 0), 12)
        gx, gy = np.gradient(g)
        grad = np.hypot(gx, gy)
        mu = cv2.blur(y, (15, 15)); sd = np.sqrt(np.maximum(cv2.blur(y * y, (15, 15)) - mu * mu, 0))
        blob = (g > 14) & (g < 90) & (grad > .06) & (grad < 1.2) & (sd < 3)
        rep.append(dict(t=round(t, 2), dots=dots, blob_share=round(float(blob.mean()), 4)))
    fails = [r for r in rep if r["dots"] > 4 or r["blob_share"] > .012]
    return dict(frames=rep, fails=len(fails), ok=not fails)


def geom_gate(video, beats, G):
    bg = np.array(G.get("bg_rgb", (10, 10, 12)))
    x0, cy, w, r = G.get("card_x", 24), G["card_y"], G.get("card_w", 1032), G.get("radius", 38)
    x1 = x0 + w
    rep = []
    for t in times(beats):
        f = frame(video, t)
        probes = {
            "seam_rows": f[G["panel_h"] - 1:cy, 40:1040],                      # rows between panel and card
            "left_margin": f[cy + 60:cy + 400, 0:x0 - 1],
            "right_margin": f[cy + 60:cy + 400, x1 + 1:1080],
            "corner_tl": f[cy:cy + 4, x0:x0 + 4], "corner_tr": f[cy:cy + 4, x1 - 4:x1],  # outside the radius = bg
        }
        dev = {k: int(np.abs(v - bg).max()) for k, v in probes.items()}
        # the card must actually start at the declared edge: one px inside differs from bg (content)
        inside_left = float(np.abs(f[cy + 100:cy + 400, x0 + 1] - bg).mean())
        inside_top = float(np.abs(f[cy + 1, x0 + r + 10:x1 - r - 10] - bg).mean())
        bad = [k for k, v in dev.items() if v > 3] + (["card_left_edge"] if inside_left < 6 else []) + (["card_top_edge"] if inside_top < 6 else [])
        rep.append(dict(t=round(t, 2), max_dev=dev, card_edge_contrast=[round(inside_left, 1), round(inside_top, 1)], bad=bad))
    fails = [r for r in rep if r["bad"]]
    return dict(frames=rep, fails=len(fails), ok=not fails)
