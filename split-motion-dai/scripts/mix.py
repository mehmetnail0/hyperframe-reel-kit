#!/usr/bin/env python3
"""Pre-mix SFX into the cut speech (per CLAUDE.md) and normalise to -14 LUFS.

usage: python3 -I scripts/mix.py SPEECH.wav OUT.wav [SFXDIR]
SFXDIR defaults to ../kit/split-motion/sfx (+ ../kit/assets/sfx for pop_hi).
Speech stays RAW (no processing besides the final loudness gain/limiter).
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEECH, OUT = sys.argv[1], sys.argv[2]
SFX = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(ROOT), "kit", "split-motion", "sfx")
KITSFX = os.path.join(os.path.dirname(ROOT), "kit", "assets", "sfx")
VT = json.load(open(os.path.join(ROOT, "data", "edl.json")))["video_total"]
PUNCH = json.load(open(os.path.join(ROOT, "data", "edl.json")))["punch"]

# (time, file, gain)  — sparse: whoosh on chapter fly-ins/punch-ins, soft pops on
# hero entrances, ticks on list items, ONE riser into "fireworks" + the boom.
EV = [(0.00, "whoosh_big.wav", .55), (0.15, "pop_soft.wav", .35)]
for t in [3.42, 6.20, 11.08, 17.12, 19.42, 23.10, 24.86, 29.62, 31.40, 34.08, 35.42, 37.88,
          40.35, 45.18, 48.68, 49.86, 51.64, 57.50, 58.90, 61.66]:
    EV.append((t, "pop_soft.wav", .30))
for t in [3.60, 4.57, 5.52, 23.38, 23.80, 58.94, 59.20, 59.48, 13.30]:
    EV.append((t, "tick.wav", .22))
EV += [(9.18, os.path.join(KITSFX, "pop_hi.wav"), .30), (44.34, os.path.join(KITSFX, "pop_hi.wav"), .28),
       (64.98, os.path.join(KITSFX, "pop_hi.wav"), .25)]
for t in [9.75, 15.78, 32.88, 60.31]:                      # chapter fly-ins
    EV.append((t, "whoosh.wav", .55))
for a, b in PUNCH:                                           # punch-ins (subtle)
    EV.append((a - .06, "whoosh.wav", .28))
EV += [(36.30 - 2.40, "riser.wav", .42), (36.27, "boom.wav", .60), (65.22, "whoosh_big.wav", .5)]

inputs = ["-i", SPEECH]
fl = [f"[0:a]apad=whole_dur={VT:.3f},atrim=0:{VT:.3f}[sp]"]
labels = ["[sp]"]
for i, (t, f, g) in enumerate(sorted(EV)):
    path = f if os.path.isabs(f) else os.path.join(SFX, f)
    inputs += ["-i", path]
    ms = int(round(t * 1000))
    fl.append(f"[{i+1}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g},adelay={ms}|{ms}[s{i}]")
    labels.append(f"[s{i}]")
mixf = ";".join(fl) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,atrim=0:{VT:.3f}"

tmp = OUT + ".pre.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", mixf + ",alimiter=limit=0.95[m]",
                "-map", "[m]", "-ar", "48000", "-ac", "2", tmp], check=True)
# two-pass loudnorm to -14 LUFS, -1.5 dBTP
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
m = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", af, "-ar", "48000", "-ac", "2", OUT], check=True)
os.remove(tmp)
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", OUT, "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
print("\n".join(l for l in r.splitlines()[-12:] if "I:" in l or "Peak:" in l or "LRA:" in l))
print(len(EV), "sfx events")
