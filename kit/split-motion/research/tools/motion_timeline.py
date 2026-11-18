#!/usr/bin/env python3
"""Frame-diff motion timeline of a reference reel (any resolution, 9:16).

usage: python3 -I motion_timeline.py VIDEO.mp4 OUT.json [--fps 10]

Per sample (10 fps, 54x96 gray):
  layout   "split" = speaker card inset at the bottom (black left margin at y 70-95 %
           while the card interior is lit) | "full" = full-frame shot / graphic
  d_top    mean |diff| of the top panel (y 0-62 %) vs the previous sample
  d_all    mean |diff| of the whole frame
Events:
  layout_changes  split<->full switches (with run lengths)
  panel_changes   d_top > 6/255 inside split runs (object in/out, swap, push)
  cuts            d_all > 18/255 (hard cut / flash)
"""
import json, subprocess, sys
import numpy as np

VID, OUT = sys.argv[1], sys.argv[2]
FPS = int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 10
W, H = 54, 96
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VID, "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                      "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
a = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
n = len(a)
edge = a[:, 68:92, 0:2].mean(axis=(1, 2))
inner = a[:, 68:92, 6:10].mean(axis=(1, 2))
# margin column must be flat (uniform dark OR light theme background) and differ from the card
edge_std = a[:, 68:92, 0:2].std(axis=(1, 2))
layout = np.where((edge_std < 5) & (np.abs(inner - edge) > 15) & ((edge < 14) | (edge > 175)), "split", "full")
theme = np.where(edge > 175, "light", "dark")
# full frames: speaker (camera texture in the bottom quarter) vs graphic (flat background there)
bstd = a[:, 72:96].std(axis=(1, 2))
layout = np.where((layout == "full") & (bstd < 12), "graphic", layout)
layout = np.where(layout == "full", "speaker", layout)
# smooth single-sample flickers
for i in range(1, n - 1):
    if layout[i - 1] == layout[i + 1] != layout[i]:
        layout[i] = layout[i - 1]
d_top = np.r_[0, np.abs(np.diff(a[:, :60], axis=0)).mean(axis=(1, 2))]
d_all = np.r_[0, np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))]
lum_top = a[:, 4:58].mean(axis=(1, 2))

runs, s = [], 0
for i in range(1, n + 1):
    if i == n or layout[i] != layout[s]:
        runs.append({"layout": str(layout[s]), "t0": round(s / FPS, 2), "dur": round((i - s) / FPS, 2)})
        s = i
panel = [round(i / FPS, 2) for i in range(1, n) if layout[i] == "split" and layout[i - 1] == "split" and d_top[i] > 6]
# merge panel changes closer than 0.25 s
merged = []
for t in panel:
    if not merged or t - merged[-1] > 0.25:
        merged.append(t)
cuts = [round(i / FPS, 2) for i in range(1, n) if d_all[i] > 18]
split_t = float((layout == "split").sum()) / FPS
dur = n / FPS
gaps = np.diff([0] + merged + [dur]) if merged else np.array([dur])
res = {
    "video": VID.split("/")[-1], "duration": round(dur, 2), "fps_sampled": FPS,
    "split_share": round(split_t / dur, 3),
    "runs": runs,
    "n_layout_switches": len(runs) - 1,
    "full_runs_s": [r["dur"] for r in runs if r["layout"] != "split"],
    "speaker_runs_s": [r["dur"] for r in runs if r["layout"] == "speaker"],
    "graphic_runs_s": [r["dur"] for r in runs if r["layout"] == "graphic"],
    "share": {k: round(float((layout == k).sum()) / n, 3) for k in ("split", "speaker", "graphic")},
    "panel_changes": merged,
    "panel_changes_per_min_split": round(len(merged) / max(split_t, 1) * 60, 1),
    "median_gap_panel_change_s": round(float(np.median(gaps)), 2),
    "max_gap_panel_change_s": round(float(gaps.max()), 2),
    "cuts": cuts,
    "mean_top_luma": round(float(lum_top.mean()), 1),
    "light_theme_share_of_split": round(float(((theme == "light") & (layout == "split")).sum() / max(1, (layout == "split").sum())), 2),
    "d_top": [round(float(x), 1) for x in d_top],
    "d_all": [round(float(x), 1) for x in d_all],
    "layout_series": "".join({"split": "s", "speaker": "f", "graphic": "g"}[l] for l in layout),
}
json.dump(res, open(OUT, "w"), indent=1)
print(f"{res['video']}: {dur:.1f}s split {res['split_share']*100:.0f}% switches {res['n_layout_switches']} "
      f"panel chg/min {res['panel_changes_per_min_split']} med gap {res['median_gap_panel_change_s']}s")
