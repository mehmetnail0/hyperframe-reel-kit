#!/usr/bin/env python3
"""Story cut + speaker video for the split-motion harness.

  edl(plan, words, energy)            -> segments [{in,out,start}] in original seconds, every boundary
                                         snapped to the quietest 10 ms within +-0.12 s, internal pauses
                                         > 0.35 s tightened to ~0.2 s, frame grid 1/30 s
  remap_words(words, edl)             -> words on the cut timeline
  speech(raw, edl, out)               -> cut speech wav (48 kHz stereo, 6 ms fades per joint)
  base_video(raw, edl, shots, lays, out, theme)
                                      -> 1080x2040 full-range video-only: split layout = speaker card
                                         (y 1372-1900, inset 24, r 38) / speaker layout = 9:16 crop,
                                         built as parallel sub-segments (one ffmpeg each, input seek,
                                         exact frame counts) + lossless concat
"""
import json, math, os, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

FPS = 30
CARD = (24, 1372, 1032, 528)   # x, y, w, h of the speaker card on the 1080x2040 canvas
BG = {"dark": "0x0a0a0c", "light": "0xe9e9ec"}


def grid(t):
    return round(t * FPS) / FPS


def snap(t, en, rad=.12):
    i0, i1 = max(0, int((t - rad) * 100)), min(len(en) - 1, int((t + rad) * 100))
    if i1 <= i0:
        return t
    best = min(range(i0, i1 + 1), key=lambda i: (en[i] + abs(i / 100 - t) * 8, abs(i / 100 - t)))
    return best / 100 + .005


def edl(plan, words, en):
    ranges = []
    for a, b in plan["keep"]:
        a, b = max(0, int(a)), min(len(words) - 1, int(b))
        if b < a:
            continue
        ranges.append((words[a]["t"] - .06, words[b]["e"] + .1, a, b))
    ranges.sort()
    segs = []
    for t0, t1, a, b in ranges:
        t0, t1 = grid(snap(t0, en)), grid(snap(t1, en))
        cur = t0
        # tighten internal pauses between consecutive words
        for i in range(a, b):
            gap0, gap1 = words[i]["e"], words[i + 1]["t"]
            if gap1 - gap0 > .35:
                c0, c1 = grid(snap(gap0 + .1, en, .06)), grid(snap(gap1 - .1, en, .06))
                if c1 - c0 > .1 and c0 > cur + .2:
                    segs.append([cur, c0])
                    cur = c1
        segs.append([cur, t1])
    out, t = [], 0.0
    for a, b in segs:
        if b - a < 2 / FPS:
            continue
        out.append(dict(i=round(a, 4), o=round(b, 4), s=round(t, 4)))
        t += b - a
    return out, round(t, 4)


def remap(x, E):
    for s in E:
        if s["i"] - 1e-6 <= x <= s["o"] + 1e-6:
            return s["s"] + x - s["i"]
    return None


def remap_words(words, E):
    out = []
    for i, w in enumerate(words):
        a = remap(w["t"], E)
        if a is None:
            continue
        b = remap(w["e"], E)
        out.append(dict(w=w["w"], t=round(a, 3), e=round(b if b is not None else a + .25, 3), src=i))
    return out


def speech(raw, E, out, sr=48000):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", raw, "-vn", "-ac", "2", "-ar", str(sr), "-f", "f32le", "pipe:1"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32).reshape(-1, 2)
    f = int(.006 * sr)
    ramp = np.linspace(0, 1, f, dtype=np.float32)[:, None]
    parts = []
    for s in E:
        seg = x[int(round(s["i"] * sr)):int(round(s["o"] * sr))].copy()
        if len(seg) > 2 * f:
            seg[:f] *= ramp
            seg[-f:] *= ramp[::-1]
        parts.append(seg)
    y = np.concatenate(parts)
    import soundfile as sf
    sf.write(out, y, sr, subtype="FLOAT")
    return len(y) / sr


def mask_png(path, theme="dark"):
    """bg-coloured frame with a transparent rounded hole for the card (corners r 38)."""
    import cv2
    c = (12, 10, 10) if theme == "dark" else (236, 233, 233)
    m = np.zeros((2040, 1080, 4), np.uint8)
    m[..., :3] = c
    m[..., 3] = 255
    x, y, w, h = CARD
    r = 38
    hole = np.zeros((2040, 1080), np.uint8)
    cv2.rectangle(hole, (x + r, y), (x + w - r, y + h), 255, -1)
    cv2.rectangle(hole, (x, y + r), (x + w, y + h - r), 255, -1)
    for cx, cy in ((x + r, y + r), (x + w - r, y + r), (x + r, y + h - r), (x + w - r, y + h - r)):
        cv2.circle(hole, (cx, cy), r, 255, -1, lineType=cv2.LINE_AA)
    m[..., 3] = 255 - hole
    m[:1370, :, 3] = 0       # the HTML panel owns the top
    m[1920:, :, 3] = 255     # sacrificial band
    cv2.imwrite(path, m)


def crop_for(src, face, layout):
    """crop rect in source px. split: card aspect, face upper-middle; speaker: 9:16 on the face."""
    W, Hs = src["w"], src["h"]
    cx = face["cx"] if face else W / 2
    cy = face["cy"] if face else Hs * .4
    fs = face["size"] if face else Hs / 6
    if layout == "speaker":
        h = Hs if W / Hs >= 9 / 16 else W * 16 / 9
        h = min(Hs, max(fs * 5.2, Hs * .78)) if Hs > 1440 else Hs  # <=1080p sources: full height (least upscaling)
        w = h * 9 / 16
        x = min(max(0, cx - w / 2), W - w)
        y = min(max(0, cy - h * .36), Hs - h)
    else:
        a = CARD[2] / CARD[3]
        w = min(W, max(fs * 6.2, W * .5))
        h = w / a
        if h > Hs:
            h, w = Hs, Hs * a
        x = min(max(0, cx - w / 2), W - w)
        y = min(max(0, cy - h * .42), Hs - h)
    ev = lambda v: int(v) // 2 * 2  # noqa
    return ev(w), ev(h), ev(x), ev(y)


def plan_subsegments(E, shots, lays):
    """split every EDL segment at camera cuts and at layout changes (cut timeline)."""
    cuts = [s["t0"] for s in shots["shots"]][1:]
    subs = []
    for s in E:
        pts = {s["i"], s["o"]}
        for c in cuts:
            if s["i"] < c < s["o"]:
                pts.add(grid(c))
        for a, b, L in lays:
            for t in (a, b):
                o = s["i"] + (t - s["s"])
                if s["i"] < o < s["o"]:
                    pts.add(grid(o))
        pts = sorted(pts)
        for a, b in zip(pts, pts[1:]):
            if b - a < .5 / FPS:
                continue
            mid_cut = s["s"] + (a + b) / 2 - s["i"]
            L = next((l for x, y, l in lays if x <= mid_cut < y), "split")
            shot = next((sh for sh in shots["shots"] if sh["t0"] <= (a + b) / 2 < sh["t1"]), shots["shots"][-1])
            subs.append(dict(i=a, o=b, layout=L, face=shot["face"]))
    # exact frame counts: assign by cumulative rounding on the cut timeline
    t, f0 = 0.0, 0
    for sb in subs:
        t += sb["o"] - sb["i"]
        f1 = int(round(t * FPS))
        sb["frames"] = max(1, f1 - f0)
        f0 = f1
    return subs


def base_video(raw, E, shots, lays, out, theme="dark", tail=0.0, jobs=None):
    src = shots["src"]
    subs = plan_subsegments(E, shots, lays)
    tail_frames = int(round(tail * FPS)) if subs else 0
    if tail_frames:  # hold the last frame for the CTA/recap tail (video only)
        subs[-1]["frames"] += tail_frames
        subs[-1]["tail"] = tail_frames / FPS
    td = tempfile.mkdtemp(prefix="kwbase_", dir=os.path.dirname(out))
    mpng = os.path.join(td, "mask.png")
    mask_png(mpng, theme)
    bg = BG.get(theme, BG["dark"])

    proxy = shots.get("proxy")

    def one(k):
        sb = subs[k]
        w, h, x, y = crop_for(src, sb["face"], sb["layout"])
        inp = raw
        if proxy and sb["layout"] != "speaker" and os.path.exists(proxy["path"]):
            f = proxy["h"] / src["h"]  # the card is downscaled anyway: cut it from the mezzanine
            w, h, x, y = (int(v * f) // 2 * 2 for v in (w, h, x, y))
            inp = proxy["path"]
        hold = f",tpad=stop_mode=clone:stop_duration={sb['tail']:.3f}" if sb.get("tail") else ""
        if sb["layout"] == "speaker":
            vf = (f"[0:v]crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,pad=1080:2040:0:0:black,fps={FPS}{hold}[v]")
        else:
            cx, cy, cw, ch = CARD
            vf = (f"[0:v]crop={w}:{h}:{x}:{y},scale={cw}:{ch}:flags=lanczos,pad=1080:2040:{cx}:{cy}:{bg},fps={FPS}{hold}[c];"
                  f"[c][1:v]overlay=0:0:shortest=1[v]")
        p = os.path.join(td, f"{k:04d}.mp4")
        dur = sb["frames"] / FPS - sb.get("tail", 0)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{sb['i']:.4f}", "-t", f"{dur + .2:.4f}", "-i", inp,
                        "-loop", "1", "-t", f"{sb['frames'] / FPS + .5:.3f}", "-i", mpng, "-filter_complex", vf, "-map", "[v]", "-frames:v", str(sb["frames"]),
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuvj420p",
                        "-color_range", "pc", "-g", "30", "-threads", "2", p], check=True)
        return p

    jobs = jobs or max(1, (os.cpu_count() or 4))
    with ThreadPoolExecutor(jobs) as ex:
        parts = list(ex.map(one, range(len(subs))))
    lst = os.path.join(td, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-movflags", "+faststart", out], check=True)
    for p in parts + [lst, mpng]:
        os.remove(p)
    os.rmdir(td)
    return len(subs)
