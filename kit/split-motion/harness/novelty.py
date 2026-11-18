#!/usr/bin/env python3
"""Novelty pass + memory: the kit must not reuse the same handful of motions every reel.

memory file (kit/split-motion/memory/history.json, committed): the last reels' fingerprints
  {"recent": [{"reel", "date", "types", "enter", "exit", "camera", "headers", "combos", "sfx_first"}]}

apply(plan, memory, seed):
  * a (type, enter, exit) combo used by any of the last 3 reels is re-rolled (enter/exit/camera
    from the verbs least used in history, seeded) — the TYPE stays (it is the meaning)
  * two consecutive beats never share an enter verb, an exit verb or a camera move
  * if > 60 % of this plan's scene types appeared in the previous reel, the most repeated
    decorative types (icon/quote/grid/orbit/radar) are swapped for types the last reel did not use
  * header styles rotate (no style three times in a row)
record(plan, memory, reel, sfx_events): appends this reel's fingerprint (keeps 12).
"""
import collections, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB = json.load(open(os.path.join(HERE, "vocab.json")))
SWAPPABLE = {"icon", "quote", "grid", "orbit", "radar", "bars", "browser", "steps", "tree"}


def load(path):
    return json.load(open(path)) if os.path.exists(path) else {"recent": []}


def _least_used(options, counts, R, avoid=()):
    c = [o for o in options if o not in avoid] or options
    m = min(counts.get(o, 0) for o in c)
    pool = [o for o in c if counts.get(o, 0) <= m + 1]
    return R.choice(pool)


def apply(plan, memory, seed):
    R = random.Random(seed * 7919 + 13)
    recent = memory.get("recent", [])[-3:]
    used_combos = {tuple(c) for r in recent for c in r.get("combos", [])}
    cnt = collections.Counter()
    for r in recent:
        cnt.update(r.get("enter", []))
        cnt.update(r.get("exit", []))
        cnt.update(r.get("camera", []))
    changes = []
    last_types = set(recent[-1]["types"]) if recent else set()
    scene_beats = [b for b in plan["beats"] if b.get("layout") != "speaker" and b.get("scene")]
    types = [b["scene"]["type"] for b in scene_beats]
    if types and last_types:
        overlap = sum(t in last_types for t in types) / len(types)
        if overlap > .6:
            fresh = [t for t in VOCAB["scenes"] if t not in last_types and t not in ("hero3d", "cta", "chapter", "custom_svg")]
            R.shuffle(fresh)
            for b in scene_beats:
                if not fresh or overlap <= .6:
                    break
                sc = b["scene"]
                if sc["type"] in SWAPPABLE and sc["type"] in last_types and sc["type"] in ("icon", "quote", "grid", "orbit", "radar"):
                    new = fresh.pop()
                    changes.append(f"type {sc['type']}->{new} (last reel overlap)")
                    sc["type"] = new
                    sc.setdefault("items", [sc.get("label") or sc.get("text") or ""])
                    types = [x["scene"]["type"] for x in scene_beats]
                    overlap = sum(t in last_types for t in types) / len(types)
    prev = {}
    for b in scene_beats:
        sc = b["scene"]
        combo = (sc["type"], sc.get("enter"), sc.get("exit"))
        if combo in used_combos or sc.get("enter") == prev.get("enter"):
            old = sc.get("enter")
            sc["enter"] = _least_used(VOCAB["enter"], cnt, R, avoid=(prev.get("enter"), old))
            changes.append(f"{sc['type']}: enter {old}->{sc['enter']}")
        if combo in used_combos or sc.get("exit") == prev.get("exit"):
            old = sc.get("exit")
            sc["exit"] = _least_used(VOCAB["exit"], cnt, R, avoid=(prev.get("exit"), old))
            changes.append(f"{sc['type']}: exit {old}->{sc['exit']}")
        if sc.get("camera") == prev.get("camera"):
            old = sc.get("camera")
            sc["camera"] = _least_used(VOCAB["camera"], cnt, R, avoid=(old,))
            changes.append(f"{sc['type']}: camera {old}->{sc['camera']}")
        cnt.update([sc["enter"], sc["exit"], sc["camera"]])
        prev = sc
    hs = [b["header"] for b in plan["beats"] if b.get("header")]
    for i in range(2, len(hs)):
        if hs[i].get("style") == hs[i - 1].get("style") == hs[i - 2].get("style"):
            hs[i]["style"] = R.choice([s for s in VOCAB["header_styles"] if s != hs[i]["style"]])
            changes.append("header style rotated")
    return plan, changes


def fingerprint(plan, reel, sfx_events=None, date=""):
    sb = [b["scene"] for b in plan["beats"] if b.get("layout") != "speaker" and b.get("scene")]
    first = collections.OrderedDict()
    for e in sfx_events or []:
        first.setdefault(e["cat"], [])
        if len(first[e["cat"]]) < 2:
            first[e["cat"]].append(e["sound"].split(":", 1)[1])
    return {"reel": reel, "date": date, "types": sorted({s["type"] for s in sb}),
            "enter": sorted({s.get("enter") for s in sb}), "exit": sorted({s.get("exit") for s in sb}),
            "camera": sorted({s.get("camera") for s in sb}),
            "headers": sorted({b["header"].get("style") for b in plan["beats"] if b.get("header")}),
            "combos": sorted({(s["type"], s.get("enter"), s.get("exit")) for s in sb}), "sfx_first": first}


def record(path, plan, reel, sfx_events=None, date=""):
    mem = load(path)
    mem["recent"] = [r for r in mem.get("recent", []) if r["reel"] != reel][-11:] + [fingerprint(plan, reel, sfx_events, date)]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(mem, open(path, "w"), indent=1, default=list)
    return mem
