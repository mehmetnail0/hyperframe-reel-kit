#!/usr/bin/env python3
"""Density QC (round 3) — fails the render when the panel is sparse or drifting.

  events_per_min   panel change EVENTS (onsets of tile-level changes > 6/255 on a 6x6 grid of the
                   motion panel, merged within 0.2 s) per minute of panel time      target 40-60
  share_ge3        share of panel time with >= 3 visible elements (DOM, validator)    >= 0.95
  lonely_share     share of panel time with a single lonely object (DOM)             <= 0.05
  ambient_share    jumps.py ambient-motion share of hold frames                      <= 0.20
  jumps_flagged    jumps.py flagged frames                                           == 0
"""
import numpy as np


def video_events(path, panel_iv, cap_top, fps=30):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import jumps
    a = jumps.frames(path, 150, cap_top - 8)
    n, H, W = a.shape
    th, tw = H // 6, W // 6
    t = a[:, :th * 6, :tw * 6].reshape(n, 6, th, 6, tw)
    dt = np.r_[np.zeros((1, 36)), np.abs(np.diff(t, axis=0)).mean(axis=(2, 4)).reshape(n - 1, 36)]
    active = (dt > 6).any(axis=1)
    panel = np.zeros(n, bool)
    for a0, b0 in panel_iv:
        panel[int(a0 * fps):int(b0 * fps)] = True
    ev, last = [], -99
    for i in range(1, n):
        if panel[i] and active[i] and not active[i - 1] and i - last > .2 * fps:
            ev.append(i / fps)
            last = i
    secs = panel.sum() / fps
    return dict(events=len(ev), panel_s=round(float(secs), 1), events_per_min=round(len(ev) / max(1, secs) * 60, 1))


def verdict(vid_ev, dom, jumps_r):
    secs = dom.get("sections", [])
    w = [max(1, s["n"]) for s in secs]
    share = float(np.average([s["share_ge3"] for s in secs], weights=w)) if secs else 0
    lonely = float(np.average([s["lonely_share"] for s in secs], weights=w)) if secs else 1
    r = dict(events_per_min=vid_ev["events_per_min"], share_ge3=round(share, 3), lonely_share=round(lonely, 3),
             ambient_share=jumps_r["ambient_motion_share"], jumps_flagged=jumps_r["flagged"])
    fails = []
    if not 40 <= r["events_per_min"] <= 60:
        fails.append(f"events/min {r['events_per_min']} (40-60)")
    if share < .95:
        fails.append(f">=3 elements only {share:.0%} of panel time (>= 95 %)")
    if lonely > .05:
        fails.append(f"lonely-object time {lonely:.0%} (<= 5 %)")
    if r["ambient_share"] > .2:
        fails.append(f"ambient drift {r['ambient_share']:.0%} (<= 20 %)")
    if r["jumps_flagged"]:
        fails.append(f"{r['jumps_flagged']} jump frames")
    r["fails"] = fails
    r["pass"] = not fails
    return r
