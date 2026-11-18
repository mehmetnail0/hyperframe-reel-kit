#!/usr/bin/env python3
"""Pre-mix the member's OWN SFX into the cut speech and normalise (-14 LUFS, TP <= -1).

usage: python3 -I scripts/mix.py SPEECH.wav OUT.wav SFX_LIBRARY_DIR [--regain]

Picks, times and gains live in data/sfx-map.json (committed); the library is not.
--regain re-measures every pick against this speech and rewrites gain_db first.
All logic: kit/split-motion/sfx_mix.py.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(os.path.dirname(ROOT), "kit", "split-motion", "sfx_mix.py")
MAP = os.path.join(ROOT, "data", "sfx-map.json")
SPEECH, OUT, LIB = sys.argv[1], sys.argv[2], sys.argv[3]
VT = json.load(open(os.path.join(ROOT, "data", "edl.json")))["video_total"]
if "--regain" in sys.argv:
    subprocess.run([sys.executable, "-I", TOOL, "gain", MAP, LIB, SPEECH], check=True)
subprocess.run([sys.executable, "-I", TOOL, "mix", MAP, LIB, SPEECH, OUT, str(VT)], check=True)
