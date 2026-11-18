#!/usr/bin/env python3
"""Measure + classify every sound in a member's SFX library (nothing is copied).

usage: python3 -I sfx_library.py LIBRARY_DIR OUT.json [--jobs 4]

Per file (wav preferred over an mp3 twin with the same stem):
  dur, active_dur (envelope > -30 dB of peak), rms_db, peak_db, attack_ms (10 % -> 90 %),
  peak_ms, peak_pos (peak / active), centroid (Hz, energy-weighted), centroid_slope
  (Hz/s over the active part: > 0 = rising = riser), hf (energy share > 4 kHz),
  lf (energy share < 250 Hz), flat (spectral flatness: ~1 noise, ~0 tonal),
  then a rule-based category + a "soft" score (0-1; low attack harshness, low hf, no clip).

Categories: riser · whoosh · tick · pop · flash · shimmer · glow · low_hit · impact ·
            draw · ui_beep · reject (named or measured as cartoonish / harsh / foley / long ambience)
"""
import json, os, re, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import soundfile as sf

LIB, OUT = sys.argv[1], sys.argv[2]
JOBS = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else os.cpu_count()
SR = 44100
REJECT_NAMES = re.compile(r"kiss|chips|crisp|teeth|cartoon|ara-ara|alarm|cash register|warning|electric|"
                          r"tea|sea ambience|heartbeat|couch|wood chest|chemistry|metal friction|keyboard|"
                          r"brain_activity|blinking|game_start|clock|readout|calculating|counting|"
                          r"retro progress|progress bar|attention prompt|absorb health", re.I)
NAME_HINT = [(r"riser", "riser"), (r"whoosh|swish|swipe|swoosh", "whoosh"), (r"zoom", "whoosh"),
             (r"flash", "flash"), (r"shin|sparkle|twinkle|diamond|chimes|bell", "shimmer"),
             (r"hologram", "glow"), (r"marker|brush|draw line|pen", "draw"),
             (r"click|tick|tab select|switch|gear|button|tuping", "tick"),
             (r"pop|plop|bloop|blip", "pop"), (r"hit|impact", "impact"),
             (r"success|confirm|positive|sweet ui|ui open|interface|futuris", "ui_beep")]


def load(p):
    try:
        x, sr = sf.read(p, always_2d=True, dtype="float32")
    except Exception:
        import librosa
        x, sr = librosa.load(p, sr=None, mono=False)
        x = np.atleast_2d(x).T
    x = x.mean(axis=1)
    x = x - x.mean()  # DC offset skews centroid / low share
    if sr != SR:
        import librosa
        x = librosa.resample(x, orig_sr=sr, target_sr=SR)
    return x


def measure(rel):
    p = os.path.join(LIB, rel)
    x = load(p)
    dur = len(x) / SR
    hop, n = 441, 2048
    frames = max(1, (len(x) - n) // hop + 1) if len(x) > n else 1
    xp = np.pad(x, (0, max(0, n - len(x))))
    env = np.array([np.sqrt(np.mean(xp[i * hop:i * hop + n] ** 2) + 1e-12) for i in range(frames)])
    edb = 20 * np.log10(env + 1e-9)
    pk = int(edb.argmax())
    act = np.where(edb > edb.max() - 30)[0]
    a0, a1 = (act[0], act[-1]) if len(act) else (0, frames - 1)
    lin = env / env.max()
    pre = lin[a0:pk + 1]
    i10 = a0 + (np.argmax(pre >= .1) if len(pre) else 0)
    i90 = a0 + (np.argmax(pre >= .9) if len(pre) else 0)
    win = np.hanning(n)
    spec = np.abs(np.array([np.fft.rfft(xp[i * hop:i * hop + n] * win) for i in range(frames)])) ** 2
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[:, f < 30] = 0  # ignore DC / sub rumble
    tot = spec.sum(axis=1) + 1e-12
    cen = (spec * f).sum(axis=1) / tot
    w = tot[a0:a1 + 1]
    cen_mean = float((cen[a0:a1 + 1] * w).sum() / w.sum())
    t = np.arange(a0, a1 + 1) * hop / SR
    slope = float(np.polyfit(t, cen[a0:a1 + 1], 1, w=np.sqrt(w))[0]) if a1 - a0 > 4 else 0.0
    E = spec[a0:a1 + 1].sum(axis=0)
    hf = float(E[f > 4000].sum() / E.sum())
    lf = float(E[f < 250].sum() / E.sum())
    band = spec[a0:a1 + 1][:, (f > 100) & (f < 16000)]
    gm = np.exp(np.mean(np.log(band + 1e-10), axis=1))
    am = np.mean(band, axis=1) + 1e-10
    flat = float(np.median(gm / am))
    # loudness growth over the active part (riser = energy rises to a late peak)
    r = dict(file=rel, dur=round(dur, 3), active_dur=round((a1 - a0 + 1) * hop / SR, 3),
             rms_db=round(float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)), 1),
             peak_db=round(float(20 * np.log10(np.abs(x).max() + 1e-9)), 1),
             attack_ms=int(max(0, i90 - i10) * hop / SR * 1000), peak_ms=int(pk * hop / SR * 1000),
             peak_pos=round((pk - a0) / max(1, a1 - a0), 2), centroid=int(cen_mean),
             centroid_slope=int(slope), hf=round(hf, 3), lf=round(lf, 3), flat=round(flat, 3))
    r["category"], r["why"] = classify(r)
    harsh = min(1, max(0, (r["centroid"] - 2500) / 5000)) * (1 if r["attack_ms"] < 15 else .5)
    r["soft"] = round(max(0, 1 - harsh - .5 * max(0, r["hf"] - .35) - (.3 if r["peak_db"] > -0.3 else 0)), 2)
    return r


def classify(r):
    name = os.path.basename(r["file"])
    if REJECT_NAMES.search(name):
        return "reject", "name: foley/cartoon/alarm/long-ambience"
    if r["dur"] > 9:
        return "reject", "too long for a hit (ambience/bed)"
    hint = next((c for pat, c in NAME_HINT if re.search(pat, name, re.I)), None)
    A, D, P = r["attack_ms"], r["active_dur"], r["peak_pos"]
    if D >= 1.2 and P > .5 and A > 700:
        m = "riser"
    elif D < .18 or (D < .3 and A < 12):
        m = "tick"
    elif r["lf"] > .45 and A < 40:
        m = "low_hit"
    elif r["flat"] > .12 and .25 < D < 3.5 and A > 40:
        m = "whoosh"
    elif r["centroid"] > 4500 and D > .35:
        m = "shimmer"
    elif D < .6 and r["flat"] < .1:
        m = "pop"
    elif A > 60 and r["flat"] < .1:
        m = "glow"
    elif A < 15 and r["centroid"] > 2500:
        m = "impact"
    else:
        m = "other"
    if m == "riser" and hint in (None, "whoosh", "riser", "glow", "shimmer"):
        return "riser", "measured (slow swell to a late peak)" + (f", name {hint}" if hint else "")
    if hint and hint != m:
        # name wins when the measurement is compatible; record both
        if hint == "riser" and D > 1.0:
            return "riser", f"name+measure (measured {m})"
        if hint in ("flash", "shimmer", "glow", "draw", "ui_beep", "whoosh", "pop", "tick", "impact"):
            return hint, f"name (measured {m})"
    return m, "measured" + (f" (name {hint})" if hint else "")


def main():
    files = []
    for root, _, fs in os.walk(LIB):
        for f in fs:
            if f.lower().endswith((".wav", ".mp3", ".aif", ".aiff", ".flac", ".m4a", ".ogg")):
                files.append(os.path.relpath(os.path.join(root, f), LIB))
    stems = {}
    for f in sorted(files):
        k = os.path.splitext(f)[0]
        if k not in stems or f.lower().endswith(".wav"):
            stems[k] = f
    todo = sorted(stems.values())
    with ProcessPoolExecutor(JOBS) as ex:
        res = list(ex.map(measure, todo))
    cats = {}
    for r in res:
        cats.setdefault(r["category"], []).append(r["file"])
    json.dump({"library_files": len(files), "unique_sounds": len(res),
               "by_category": {k: len(v) for k, v in sorted(cats.items())}, "sounds": res},
              open(OUT, "w"), indent=1, ensure_ascii=False)
    print(len(files), "files,", len(res), "unique:", {k: len(v) for k, v in sorted(cats.items())})


if __name__ == "__main__":
    main()
