#!/usr/bin/env python3
"""Build the SFX PALETTE (categories -> several files from the member's library).

usage: python3 -I build_palette.py SFX_LIB.json LIBRARY_DIR palette.json

SFX_LIB.json = research/tools/sfx_library.py output (measured type/length/brightness).
The palette is a committed list of FILE NAMES + processing; the audio never leaves the
member's machine. For each pick we also cache `max_m` (max momentary loudness after the
processing chain) so the mixer never re-measures a file (gain = voice_I - under_voice - max_m).

Levels (under_voice_db) = Kallaway medians (research/kallaway-20.md: risers/glows -8 dB, pops -14, ticks -26
vs the voice) made ~4 dB gentler, per the member: "low, gentleman-like, but not too quiet".

Category rules (soft / smooth / Kallaway-style: light cinematic risers, tiny soft ticks,
occasional flash, soft glows; harsh = fast attack + centroid > 6 kHz unless low-passed):
"""
import json, os, re, subprocess, sys

SPEC = {
    # cat: (selector over measured sounds, processing, under_voice_db, role notes)
    "riser_cine": dict(pick=lambda r: r["category"] == "riser" and r["centroid"] < 1200 and r["attack_ms"] >= 1000,
                       lowpass=0, fade=30, under=12, note="light cinematic swell, peak on the hit (chapter / reveal / punch-in)"),
    "riser_short": dict(pick=lambda r: r["category"] == "riser" and r["centroid"] < 1200 and 600 <= r["attack_ms"] < 1000,
                        lowpass=0, fade=20, under=12, note="0.7-1 s swell into a scene swap"),
    "riser_air": dict(pick=lambda r: r["category"] == "riser" and r["centroid"] >= 1200,
                      lowpass=6500, fade=40, under=16, note="bright digital riser, low-passed; rare, under a big reveal"),
    "whoosh_soft": dict(pick=lambda r: r["category"] == "whoosh" and 350 <= r["centroid"] <= 2200 and r["active_dur"] <= 1.2 and r["soft"] >= .9,
                        lowpass=9000, fade=10, under=15, note="panel swap / object slide"),
    "whoosh_deep": dict(pick=lambda r: r["category"] == "whoosh" and r["centroid"] < 350 and r["lf"] > .5 and r["active_dur"] <= 2.2,
                        lowpass=0, fade=15, under=14, note="layout switch (panel <-> full speaker), chapter fly-through"),
    "tick_soft": dict(pick=lambda r: r["file"] in TICKS, lowpass=7000, fade=3, under=18,
                      note="pit pit pit: counters, list rows, small text reveals"),
    "flash": dict(pick=lambda r: r["category"] == "flash", lowpass=8500, fade=2, under=14,
                  note="white flash frame / camera-flash reveal; max 1-2 per reel"),
    "glow": dict(pick=lambda r: r["file"] in GLOWS, lowpass=8000, fade=25, under=13,
                 note="soft shimmer/glow on a hero landing; never two in a row"),
    "ding": dict(pick=lambda r: r["file"] in DINGS, lowpass=8000, fade=5, under=16,
                 note="soft bell/ding on a key word or a check mark"),
    "draw": dict(pick=lambda r: r["category"] == "draw" and "Marker Pen" in r["file"], lowpass=7500, fade=10, under=20,
                 note="line / underline / highlighter draws"),
    "low_swell": dict(pick=lambda r: r["file"] in LOWS, lowpass=0, fade=20, under=16,
                      note="sub swell under the hook or the CTA (felt, not heard)"),
}
TICKS = {"Infographic Jan 8 2025 (1)/Infographic 01 Plop (1).wav", "Infographic Jan 8 2025 (1)/Infographic 08 Bloop (1).wav",
         "Infographic Jan 8 2025 (1)/Infographic 04 Blip (1).wav", "casual-click-pop-ui-1-262118 (1).mp3",
         "start-13691 (1).mp3", "UI Draw Sound Effects (1)/UI Button 1 (1).wav", "UI Draw Sound Effects (1)/UI Button 2 (1).wav",
         "UI Draw Sound Effects (1)/UI Button 3 (1).wav", "UI Tab Select (1).wav"}
GLOWS = {"shine-4-268912 (1).mp3", "shine-6-268910 (1).mp3", "sound-effect-twinklesparkle-115095 (1).mp3", "Shining (1).wav",
         "shine-02-355934 (1).mp3", "Hologram Appears (1).wav", "Progress Hover 01 (1).wav", "Progress Hover 03 (1).wav",
         "SyntheticDesign EC08_32_1 (1).wav", "shining-anime-sound-effect-240582 (1).mp3"}
DINGS = {"Infographic Jan 8 2025 (1)/Infographic 19 Bell (1).wav", "Infographic Jan 8 2025 (1)/Infographic 02 Swipe Ding (1).wav",
         "Confirmation Tone (1).wav", "Successes (1)/Success 3 (1).wav", "Success (1).wav"}
LOWS = {"Mountain Audio - Deep Whoosh (1).wav", "Whoosh Sound Effects Jan 15 2025 (1)/Whoosh Logo 01 (1).wav"}


def max_m(path, lowpass, fade):
    af = ["aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo"]
    if lowpass:
        af.append(f"lowpass=f={lowpass}:p=2")
    af += [f"afade=t=in:d={fade / 1000:.3f}", "apad=pad_dur=0.6", "ebur128"]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", ",".join(af), "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace").stderr
    ms = [float(x) for x in re.findall(r"M:\s*(-?[\d.]+)", r)]
    return round(max(ms), 1) if ms else -70.0


def main(lib_json, lib_dir, out):
    lib = json.load(open(lib_json))["sounds"]
    pal = {"_comment": "SFX palette: categories -> files in the member's OWN library (names only; audio never committed). "
                       "Built by kit/split-motion/sfx/build_palette.py from research/tools/sfx_library.py measurements.",
           "categories": {}}
    used = set()
    for cat, sp in SPEC.items():
        picks = [r for r in lib if r["category"] != "reject" and sp["pick"](r) and r["file"] not in used]
        picks.sort(key=lambda r: (-r["soft"], r["file"]))
        files = []
        for r in picks[:8]:
            used.add(r["file"])
            files.append(dict(file=r["file"], dur=r["dur"], peak_ms=r["peak_ms"], attack_ms=r["attack_ms"],
                              centroid=r["centroid"], max_m=max_m(os.path.join(lib_dir, r["file"]), sp["lowpass"], sp["fade"])))
        pal["categories"][cat] = dict(lowpass=sp["lowpass"], fade_in_ms=sp["fade"], under_voice_db=sp["under"],
                                      note=sp["note"], files=files)
        print(f"{cat:12s} {len(files)} files")
    json.dump(pal, open(out, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(*sys.argv[1:4])
