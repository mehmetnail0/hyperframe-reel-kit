#!/usr/bin/env python3
"""QC + auto-fix for the split-motion harness.

  dom_fit(index_html, beats)  -> {sid: scale}  scenes whose drawn box leaves the stage (x 40-1040,
                                 y 335-1205 in split = between header and seam caption; y 140-1540
                                 for graphic) get a shrink factor; the compiler re-emits them scaled
  final(video, work, beats, face_box) -> report: loudness (I, TP), motion (static runs / gaps in
                                 the panel at 10 fps), near-empty panel frames, caption-vs-face overlap
                                 in speaker beats, 2 fps contact sheet
"""
import json, os, re, subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SAFE = {"split": (40, 335, 1040, 1205), "graphic": (40, 300, 1040, 1540)}


def set_geometry(G):
    """split stage = between the header and the seam caption of the current geometry"""
    SAFE["split"] = (40, G["stage_top"] + 4, 1040, G["cap_top"] - 12)


def dom_fit(index_html, beats, work, screen_fit=None):
    # QC copy without the <video>/<audio> (the base video may still be encoding in parallel)
    src = open(index_html).read()
    src = re.sub(r'<video[^>]*></video>', '', src)
    src = re.sub(r'<audio[^>]*></audio>', '', src)
    src = re.sub(r'<script type="(importmap|module)">.*?</script>', '', src, flags=re.S)  # ES modules fail on file://
    qh = os.path.join(os.path.dirname(os.path.abspath(index_html)), "_qc.html")
    open(qh, "w").write(src)
    index_html = qh
    bj = os.path.join(work, "qc_beats.json")
    oj = os.path.join(work, "qc_dom.json")
    json.dump(beats, open(bj, "w"))
    env = dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
    r = subprocess.run(["node", os.path.join(HERE, "qc_dom.js"), os.path.abspath(index_html), bj, oj],
                       capture_output=True, text=True, env=env)
    os.remove(qh)
    if r.returncode != 0:
        return {}, [f"dom qc skipped: {r.stderr[-300:]}"]
    fit, notes = {}, []
    dev_fail = {}
    for m in json.load(open(oj)):
        b = m["box"]
        if not b:
            notes.append(f"{m['sid']}: nothing visible at {m['t']:.2f}s")
            continue
        for d in b.get("dev", []):  # content leaving its phone/browser = FAIL -> shrink the screen content
            if d["bad"]:
                prev = (screen_fit or {}).get(m["sid"], 1)
                dev_fail[m["sid"]] = round(prev * max(.6, 1 - d["worst"] * 1.6 - .04), 3)
                notes.append(f"{m['sid']}: {d['bad']} element(s) overflow the device by {d['worst']:.0%} -> screen scale {dev_fail[m['sid']]}")
        X0, Y0, X1, Y1 = SAFE.get(m["layout"], SAFE["split"])
        cx, cy = 540, (Y0 + Y1) / 2
        need = 1.0
        for v, lim, c in ((b["x0"], X0, cx), (b["x1"], X1, cx), (b["y0"], Y0, cy), (b["y1"], Y1, cy)):
            if (v < lim and v < c) or (v > lim and v > c):
                need = min(need, abs(lim - c) / max(1, abs(v - c)))
        if need < .995:
            fit[m["sid"]] = round(max(.55, need * .98), 3)
        else:  # too small: grow until the box touches the safe stage (Kallaway heroes fill 60-90 %)
            g = min((X1 - cx) / max(1, b["x1"] - cx), (cx - X0) / max(1, cx - b["x0"]),
                    (Y1 - cy) / max(1, b["y1"] - cy), (cy - Y0) / max(1, cy - b["y0"]))
            g = min(2.1, g * .97)  # the shorter panel scales the 880-px design frame down: allow a bigger regrow
            if g > 1.06:
                fit[m["sid"]] = round(g, 3)
        if m["sid"] in fit:
            notes.append(f"{m['sid']}: box {int(b['x0'])},{int(b['y0'])}-{int(b['x1'])},{int(b['y1'])} -> scale {fit[m['sid']]}")
    if screen_fit is not None:
        return fit, notes, dev_fail
    return fit, notes


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace").stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return float(i[-1]), float(tp[-1])


def motion(path, beats, fps=10, panel_h=1370):
    W, Hp = 108, int(panel_h / 10)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},crop=1080:{panel_h}:0:0,scale={W}:{Hp},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, Hp, W).astype(np.int16)
    d = np.r_[0, np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))]
    n = len(a)
    split = np.zeros(n, bool)
    for b in beats:
        if b["layout"] != "speaker":
            split[int(b["t0"] * fps):int(b["t1"] * fps)] = True
    runs, cur = [], 0
    for i in range(n):
        if split[i] and d[i] < .6:
            cur += 1
        else:
            if cur:
                runs.append(cur / fps)
            cur = 0
    lit = (a[:, 30:max(31, Hp - 15)] > 70).mean(axis=(1, 2))
    empty = float(((lit < .012) & split).sum() / fps)
    majors = [i / fps for i in range(n) if d[i] > 6 and split[i]]
    gaps = np.diff([0] + majors + [n / fps]) if majors else np.array([n / fps])
    return dict(longest_static_s=round(max(runs, default=0), 2), static_over_5s=sum(r > 5 for r in runs),
                major_changes_per_min=round(len(majors) / (split.sum() / fps) * 60, 1) if split.sum() else 0,
                longest_gap_s=round(float(gaps.max()), 2), near_empty_s=round(empty, 2))


def sheet(path, out, cols=16):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf",
                    f"fps=2,scale=120:214,drawtext=text='%{{pts\\:hms}}':x=3:y=3:fontsize=13:fontcolor=yellow:box=1:boxcolor=black@0.6,tile={cols}x10",
                    "-frames:v", "1", out], check=True)


def final(video, beats, face_cap, out_dir, panel_h=1370):
    I, tp = loudness(video)
    mo = motion(video, beats, panel_h=panel_h)
    sheet(video, os.path.join(out_dir, "sheet-v.jpg"))
    issues = []
    if abs(I + 14) > .6:
        issues.append(f"loudness {I} LUFS")
    if tp > -1.0:
        issues.append(f"true peak {tp}")
    if mo["static_over_5s"]:  # holds are welcome (stillness by default), dead panels are not
        issues.append(f"{mo['static_over_5s']} static runs > 5 s")
    if face_cap and face_cap.get("overlap"):
        issues.append("speaker caption overlaps the mouth")
    return dict(lufs=I, true_peak=tp, motion=mo, issues=issues)
