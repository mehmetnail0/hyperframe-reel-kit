#!/usr/bin/env python3
"""Aggregate per-reel research outputs into research/kallaway-20.json.

usage: python3 -I aggregate.py WORK_DIR index.tsv OUT.json
  WORK_DIR/diff/<id>.json  motion_timeline.py     WORK_DIR/ev/<id>.json  sfx_events.py
  WORK_DIR/tr/<id>/words.json  transcript          WORK_DIR/music_id.json music_id.py
"""
import collections, csv, json, os, sys
import numpy as np

W, IDX, OUT = sys.argv[1:4]
meta = {r["id"]: r for r in csv.DictReader(open(IDX), delimiter="\t")}
mid = json.load(open(os.path.join(W, "music_id.json")))
reels = []
agg = collections.defaultdict(list)
for i in sorted(meta):
    mo = json.load(open(os.path.join(W, "diff", i + ".json")))
    ev = json.load(open(os.path.join(W, "ev", i + ".json")))
    tr = json.load(open(os.path.join(W, "tr", i, "words.json")))
    words = tr["words"]
    dur = ev["duration"]
    syn = [e for e in ev["events"] if e["synced"]]
    hook_end = next((x["e"] for x in words if x["w"].endswith((".", "?", "!"))), 4.0)
    cta = [x["t"] for x in words if "comment" in x["w"].lower()]
    cta_t = cta[-1] if cta else None
    def rate(lo, hi, evs):
        n = sum(lo <= e["t"] < hi for e in evs)
        return round(n / max(.5, hi - lo) * 60, 1)
    sp_runs = mo["speaker_runs_s"]
    split_runs = [r["dur"] for r in mo["runs"] if r["layout"] == "split"]
    spk_starts = [r["t0"] for r in mo["runs"] if r["layout"] == "speaker"]
    types = collections.Counter(e["type"] for e in syn)
    gaps = np.diff([e["t"] for e in syn]) if len(syn) > 1 else np.array([0])
    same_cat_b2b = sum(1 for a, b in zip(syn, syn[1:]) if a["type"] == b["type"])
    r = {
        "id": i, "date": meta[i]["upload_date"], "duration_s": dur, "res": f"{meta[i]['width']}x{meta[i]['height']}",
        "hook": " ".join(x["w"] for x in words if x["t"] < hook_end), "hook_s": round(hook_end, 2),
        "cta_comment_at_s": round(cta_t, 1) if cta_t else None,
        "wpm": round(len(words) / words[-1]["e"] * 60),
        "layout_share": mo["share"], "layout_switches": mo["n_layout_switches"],
        "speaker_runs_s": sp_runs, "split_runs_median_s": round(float(np.median(split_runs)), 2) if split_runs else None,
        "light_theme_share": mo["light_theme_share_of_split"],
        "panel_changes_per_min": mo["panel_changes_per_min_split"], "median_gap_panel_change_s": mo["median_gap_panel_change_s"],
        "sfx": {"synced_per_min": round(len(syn) / dur * 60, 1), "loose_per_min": ev["sfx_per_min"],
                "types_synced": dict(types), "risers_synced": types.get("riser", 0),
                "level_vs_voice_db_by_type": ev["level_by_type"], "median_gap_s": round(float(np.median(gaps)), 2),
                "same_sound_back_to_back": ev["back_to_back_same"], "same_type_back_to_back_synced": same_cat_b2b,
                "distinct_sounds": ev["distinct_sounds"],
                "per_min_hook": rate(0, hook_end + .5, syn), "per_min_body": rate(hook_end + .5, (cta_t or dur) - .5, syn),
                "per_min_cta": rate((cta_t or dur) - .5, dur, syn) if cta_t else None,
                "on_screen": ev["on_screen"], "visual_sync_rate": ev["visual_sync_rate"], "visual_sync_chance": ev["visual_sync_chance"]},
        "music": {**ev["music"], "identified": (mid.get(i) or {}).get("best"),
                  "windows_matched": sum(1 for w in (mid.get(i) or {}).get("windows", []) if w["match"])},
    }
    r["music"].pop("curve_2s_vs_voice_db", None)
    reels.append(r)
    for k, v in (("synced_per_min", r["sfx"]["synced_per_min"]), ("loose_per_min", r["sfx"]["loose_per_min"]),
                 ("risers_per_min", r["sfx"]["risers_synced"] / dur * 60), ("bed_vs_voice_db", ev["music"]["bed_vs_voice_db"]),
                 ("split_share", mo["share"]["split"]), ("speaker_share", mo["share"]["speaker"]),
                 ("graphic_share", mo["share"]["graphic"]), ("layout_switches_per_min", mo["n_layout_switches"] / dur * 60),
                 ("panel_changes_per_min", mo["panel_changes_per_min_split"]), ("hook_s", hook_end), ("wpm", r["wpm"]),
                 ("per_min_hook", r["sfx"]["per_min_hook"]), ("per_min_body", r["sfx"]["per_min_body"]),
                 ("gap_s", float(np.median(gaps))), ("same_type_b2b_share", same_cat_b2b / max(1, len(syn) - 1)),
                 ("same_sound_b2b", ev["back_to_back_same"]), ("tempo", ev["music"]["tempo_bpm"] or 0)):
        agg[k].append(v)
    if r["sfx"]["per_min_cta"] is not None:
        agg["per_min_cta"].append(r["sfx"]["per_min_cta"])
    for s in sp_runs:
        agg["speaker_run_s"].append(s)
    for a, b in zip(spk_starts, spk_starts[1:]):
        agg["speaker_every_s"].append(b - a)
    for e in syn:
        agg["lvl_" + e["type"]].append(e["level_vs_voice_db"])
        agg["type_" + e["type"]].append(1)

def st(v):
    v = np.array(v, float)
    return {"median": round(float(np.median(v)), 2), "p25": round(float(np.percentile(v, 25)), 2),
            "p75": round(float(np.percentile(v, 75)), 2), "n": int(len(v))}

tot_types = {k[5:]: len(v) for k, v in agg.items() if k.startswith("type_")}
s = sum(tot_types.values())
summary = {k: st(v) for k, v in agg.items() if not k.startswith(("type_", "lvl_"))}
summary["type_mix_synced_share"] = {k: round(v / s, 3) for k, v in sorted(tot_types.items(), key=lambda x: -x[1])}
summary["level_vs_voice_db_synced"] = {k[4:]: st(v) for k, v in agg.items() if k.startswith("lvl_")}
summary["music_tracks"] = collections.Counter(
    (r["music"]["identified"] or {}).get("title", "unidentified") + " — " + (r["music"]["identified"] or {}).get("artist", "")
    for r in reels)
json.dump({"source": "20 most recent reels of the creator (2026-10-29 -> 11-18), measured by kit/split-motion/research/tools/*",
           "method_notes": {
               "stems": "demucs htdemucs --two-stems vocals (CPU)",
               "sfx": "spectral novelty of the no-vocals stem vs a 4 s per-band median; 'synced' = an event on a top-10% frame change "
                      "(-0.1..+0.2 s; risers at their peak +-0.3 s). Synced counts are the conservative SFX numbers; 'loose' includes "
                      "music percussion that survived the beat-grid filter.",
               "level": "event peak (100 ms RMS, bed power removed) minus the voice's active RMS",
               "layout": "split = flat margin column beside a lit speaker card; graphic = flat bottom quarter; else speaker"},
           "summary": summary, "reels": reels}, open(OUT, "w"), indent=1, ensure_ascii=False, default=int)
print(json.dumps(summary, indent=1, default=int)[:4000])
