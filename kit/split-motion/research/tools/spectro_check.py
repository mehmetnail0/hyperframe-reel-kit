#!/usr/bin/env python3
"""Spectrogram of a stem with detected events marked (visual QC of sfx_events.py).
usage: python3 -I spectro_check.py NO_VOCALS.wav EVENTS.json OUT.png [T0 T1]"""
import json, sys
import numpy as np, soundfile as sf, librosa
import cv2
wav, ev, out = sys.argv[1:4]
t0, t1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0, 40)
x, sr = sf.read(wav, always_2d=True, dtype="float32"); x = x.mean(axis=1)
x = x[int(t0 * sr):int(t1 * sr)]
S = librosa.amplitude_to_db(np.abs(librosa.stft(x, n_fft=2048, hop_length=sr // 50)), ref=np.max)
mel = librosa.feature.melspectrogram(S=librosa.db_to_power(S) , sr=sr, n_mels=160)
img = librosa.power_to_db(mel, ref=np.max)
img = np.clip((img + 70) / 70 * 255, 0, 255).astype(np.uint8)[::-1]
img = cv2.applyColorMap(cv2.resize(img, (int((t1 - t0) * 50), 320)), cv2.COLORMAP_MAGMA)
d = json.load(open(ev))
col = {"riser": (0, 255, 255), "whoosh": (255, 200, 0), "tick": (255, 255, 255), "pop": (0, 255, 0),
       "flash": (255, 0, 255), "shimmer": (200, 100, 255), "glow": (0, 160, 255), "low_hit": (0, 0, 255),
       "impact": (0, 0, 200), "other": (128, 128, 128)}
pad = np.zeros((60, img.shape[1], 3), np.uint8)
img = np.vstack([img, pad])
for e in d["events"]:
    if not (t0 <= e["t"] < t1):
        continue
    x0 = int((e["t"] - t0) * 50); x1 = int((e["t"] + e["dur"] - t0) * 50)
    c = col.get(e["type"], (128, 128, 128))
    cv2.rectangle(img, (x0, 322), (max(x0 + 2, x1), 332), c, -1)
    cv2.putText(img, e["type"][:5], (x0, 350), cv2.FONT_HERSHEY_SIMPLEX, .35, c, 1)
for s in range(int(t0), int(t1) + 1):
    x = int((s - t0) * 50)
    cv2.line(img, (x, 300), (x, 320), (255, 255, 255), 1)
    if s % 5 == 0:
        cv2.putText(img, str(s), (x + 2, 314), cv2.FONT_HERSHEY_SIMPLEX, .35, (255, 255, 255), 1)
cv2.imwrite(out, img)
