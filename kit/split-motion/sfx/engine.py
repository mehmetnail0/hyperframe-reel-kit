#!/usr/bin/env python3
"""SFX engine: turns the planner's CUES into a mix map, enforcing taste in CODE.

usage: python3 -I engine.py palette.json cues.json OUT_map.json [--seed N] [--per-min 16] [--memory mem.json]

cues.json: [{"t": 3.2, "role": "chapter", "prio": 2, "run": "c1"}, ...]
  role  -> category options (first = preferred). Roles come from the scene plan:
     intro        riser_cine (+ whoosh_deep 0.05 s after the peak)  — reel open
     chapter      riser_cine                                       — chapter / big number
     reveal       riser_short | riser_cine                         — the big reveal
     punch        whoosh_deep | riser_short                        — panel -> full speaker
     back         whoosh_soft                                      — full speaker -> panel
     swap         whoosh_soft | whoosh_deep                        — scene swap inside the panel
     counter      tick_soft  (a run: 1-2-3, list rows, counters)   — the ONLY category allowed back to back
     tick         tick_soft                                        — single small text reveal
     flash        flash                                            — white flash frame (<= 2 per reel)
     glow         glow | ding                                      — hero landing
     ding         ding | glow                                      — check mark / key word
     draw         draw                                             — line / underline / highlighter
     air          riser_air                                        — bright riser under a reveal (rare)
     cta          riser_cine + ding                                — comment CTA

Rules (all enforced here, not left to the planner):
  1. never the same FILE twice in a row (global), and a file is not reused until every other
     file of its category was used (seeded rotation; the memory file biases the start away
     from what the previous reels used first)
  2. a CATEGORY never sits on two consecutive events, except inside a counter run
     (ticks) — then files alternate inside the run
  3. density: at most `per_min` events per minute (research median, see research/kallaway-20.md);
     lowest-priority cues are dropped first; min gap 0.35 s (0.12 s inside a counter run)
  4. per-category caps per reel: flash <= 2, air <= 1, glow <= 4, ding <= 3
  5. levels: each category's under_voice_db (palette) — the mixer turns that into gain
"""
import json, os, random, sys

ROLE = {
    "intro": ["riser_cine"], "chapter": ["riser_cine", "riser_short"], "reveal": ["riser_short", "riser_cine"],
    "punch": ["whoosh_deep", "riser_short"], "back": ["whoosh_soft", "whoosh_deep"],
    "swap": ["whoosh_soft", "whoosh_deep"], "counter": ["tick_soft"], "tick": ["tick_soft"],
    "flash": ["flash"], "glow": ["glow", "ding"], "ding": ["ding", "glow"], "draw": ["draw", "tick_soft"],
    "air": ["riser_air"], "cta": ["riser_cine"], "low": ["low_swell", "whoosh_deep"],
}
CAPS = {"flash": 2, "riser_air": 1, "glow": 4, "ding": 3, "low_swell": 1}
ALIGN_PEAK = {"riser_cine", "riser_short", "riser_air", "whoosh_deep", "whoosh_soft", "low_swell", "glow"}
PRIO_DEFAULT = {"intro": 5, "chapter": 4, "reveal": 4, "cta": 4, "punch": 3, "flash": 3, "counter": 2, "back": 2,
                "swap": 1, "glow": 1, "ding": 1, "tick": 1, "draw": 1, "air": 2, "low": 1}


def plan(palette, cues, seed=0, per_min=14.0, total=None, memory=None):
    rng = random.Random(seed)
    cats = palette["categories"]
    order = {}
    for c, v in cats.items():
        files = [f["file"] for f in v["files"]]
        rng.shuffle(files)
        recent = (memory or {}).get("sfx_first", {}).get(c, [])
        files.sort(key=lambda f: f in recent)  # stable: files the last reels opened with go last
        order[c] = files
    ptr = {c: 0 for c in cats}
    cues = sorted(cues, key=lambda c: c["t"])
    for c in cues:
        c.setdefault("prio", PRIO_DEFAULT.get(c["role"], 1))
    # 3. density budget
    total = total or (cues[-1]["t"] + 2 if cues else 60)
    budget = int(per_min * total / 60 + .5)
    keep = sorted(cues, key=lambda c: (-c["prio"], c["t"]))[:budget]
    keep = sorted(keep, key=lambda c: c["t"])
    events, used_cat, last_file, last_cat, last_t, last_run = [], {}, None, None, -9, None
    for c in keep:
        in_run = c.get("run") is not None and c.get("run") == last_run and c["role"] == "counter"
        gap = .12 if in_run else .35
        if c["t"] - last_t < gap:
            continue
        choice = None
        for cat in ROLE.get(c["role"], [c["role"]]):
            if cat not in cats or not cats[cat]["files"]:
                continue
            if cat == last_cat and not in_run:
                continue  # rule 2
            if used_cat.get(cat, 0) >= CAPS.get(cat, 99):
                continue  # rule 4
            choice = cat
            break
        if choice is None:
            continue
        files = order[choice]
        f = files[ptr[choice] % len(files)]
        if f == last_file and len(files) > 1:  # rule 1
            ptr[choice] += 1
            f = files[ptr[choice] % len(files)]
        ptr[choice] += 1
        events.append(dict(t=round(c["t"], 3), sound=f"{choice}:{f}", cat=choice, role=c["role"],
                           align="peak" if choice in ALIGN_PEAK else "start", why=c.get("why", c["role"])))
        used_cat[choice] = used_cat.get(choice, 0) + 1
        last_file, last_cat, last_t, last_run = f, choice, c["t"], c.get("run")
        if c["role"] == "intro" and "whoosh_deep" in cats:  # riser lands into a soft deep whoosh
            g = order["whoosh_deep"][ptr["whoosh_deep"] % len(order["whoosh_deep"])]
            ptr["whoosh_deep"] += 1
            events.append(dict(t=round(c["t"] + .05, 3), sound=f"whoosh_deep:{g}", cat="whoosh_deep", role="intro",
                               align="start", why="intro tail"))
            last_file, last_cat = g, "whoosh_deep"
    return events, budget, len(cues)


def to_map(palette, events, lib_hint=""):
    cats = palette["categories"]
    sounds = {}
    for e in events:
        cat, f = e["sound"].split(":", 1)
        meta = next(x for x in cats[cat]["files"] if x["file"] == f)
        sounds[e["sound"]] = dict(file=f, peak_ms=meta["peak_ms"], fade_in_ms=cats[cat]["fade_in_ms"],
                                  lowpass=cats[cat]["lowpass"], under_voice_db=cats[cat]["under_voice_db"],
                                  max_m=meta["max_m"])
    return {"_comment": "generated by kit/split-motion/sfx/engine.py (anti-repeat + density enforced)",
            "library_root_hint": lib_hint, "sounds": sounds, "events": events}


def check(events):
    """Assert the taste rules on a finished event list (used by QC)."""
    errs = []
    for a, b in zip(events, events[1:]):
        if a["sound"] == b["sound"]:
            errs.append(f"same file back to back at {b['t']}")
        if a["cat"] == b["cat"] and not (a["role"] == b["role"] == "counter") and a["role"] != "intro":
            errs.append(f"same category back to back at {b['t']} ({b['cat']})")
    return errs


if __name__ == "__main__":
    a = sys.argv[1:]
    pal, cues, out = json.load(open(a[0])), json.load(open(a[1])), a[2]
    seed = int(a[a.index("--seed") + 1]) if "--seed" in a else 0
    pm = float(a[a.index("--per-min") + 1]) if "--per-min" in a else 16.0
    mem = json.load(open(a[a.index("--memory") + 1])) if "--memory" in a and os.path.exists(a[a.index("--memory") + 1]) else None
    ev, budget, n = plan(pal, cues, seed, pm, memory=mem)
    errs = check(ev)
    json.dump(to_map(pal, ev), open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(ev)} events from {n} cues (budget {budget}); rule violations: {errs or 'none'}")
