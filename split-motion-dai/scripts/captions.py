#!/usr/bin/env python3
"""One-word seam captions from the CUT speech.

usage:
  whisper-cli -m ggml-small.en.bin -f cut16.wav -ojf -of cut_words -ml 1 -sow --dtw small.en -nfa
  python3 -I scripts/captions.py cut_words.json cut16.wav  -> data/words.json

Onset estimate = whisper DTW token time - 0.10 s, then snapped to the nearest
energy onset (a 10 ms frame rising above -40 dBFS after >=20 ms below it)
within [-0.22, +0.10] s. Cheap and good to ~1 frame for one-word captions.
"""
import array, json, math, os, sys, wave

J, WAV = sys.argv[1], sys.argv[2]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = {"Z.": "zero.", "Z": "zero", "gotta": "gotta"}
DROP = {"-", "--"}

w = wave.open(WAV); sr = w.getframerate()
s = array.array("h", w.readframes(w.getnframes())); w.close()
hop = sr // 100
db = []
for i in range(0, len(s) - hop, hop):
    seg = s[i:i + hop]
    db.append(20 * math.log10(math.sqrt(sum(v * v for v in seg) / hop) / 32768 + 1e-9))
onsets = [i / 100 for i in range(2, len(db)) if db[i] > -40 and db[i - 1] <= -40 and db[i - 2] <= -40]
total = len(s) / sr

words = []
for seg in json.load(open(J))["transcription"]:
    txt = seg["text"].strip()
    if not txt or txt in DROP:
        continue
    toks = [k for k in seg["tokens"] if not k["text"].startswith("[")]
    dtw = [k["t_dtw"] / 100 for k in toks if k.get("t_dtw", -1) >= 0]
    t = (min(dtw) - 0.10) if dtw else seg["offsets"]["from"] / 1000
    cands = [o for o in onsets if t - 0.22 <= o <= t + 0.10]
    if cands:
        t = min(cands, key=lambda o: abs(o - t))
    words.append({"w": FIX.get(txt, txt), "t": round(max(0, t), 3)})

words.sort(key=lambda x: x["t"])
for i, x in enumerate(words):  # monotonic, >= 3 frames apart
    if i and x["t"] < words[i - 1]["t"] + 0.1:
        x["t"] = round(words[i - 1]["t"] + 0.1, 3)
for i, x in enumerate(words):
    nxt = words[i + 1]["t"] if i + 1 < len(words) else total
    x["d"] = math.floor(min(nxt - x["t"] - 0.004, 0.9) * 1000) / 1000
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
json.dump(words, open(os.path.join(ROOT, "data", "words.json"), "w"), indent=0)
print(len(words), "words")
print(" ".join(f"{x['t']:.2f}:{x['w']}" for x in words))
