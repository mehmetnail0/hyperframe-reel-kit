#!/usr/bin/env python3
"""SFX events + music bed of one reference reel, from demucs stems.

usage: python3 -I sfx_events.py VOCALS.wav NO_VOCALS.wav MOTION.json OUT.json

  NO_VOCALS = music + SFX residue (demucs htdemucs --two-stems vocals).
  MOTION    = motion_timeline.py output (to say what is on screen at each event).

Method (all 10 ms frames, mono):
  * bed baseline   = rolling 25th-percentile of the residue energy over 4 s (the music bed /
                     room tone; transients and risers stick out of it)
  * transient SFX  = residue energy >= baseline + 7 dB for >= 30 ms, merged within 90 ms,
                     extended until it falls back to baseline + 3 dB
  * risers         = 60 ms-smoothed residue energy climbing >= 9 dB over 0.6-4 s into a peak
                     that is >= baseline + 6 dB (a slow swell, not a transient)
  * leakage guard  = an event is dropped when the voice is >= 16 dB louder than the residue
                     peak AND the voice itself has an onset there (demucs bleed of plosives)
  * features       = duration, attack, peak, centroid (+ slope), >4 kHz / <250 Hz share,
                     spectral flatness -> the same classes as sfx_library.py
  * level vs voice = event peak (100 ms RMS, bed power removed) minus the voice's active RMS
                     (frames where the voice is within 20 dB of its 95th percentile)
  * repetition     = 24-band log-spectrum fingerprint; back-to-back "same sound" when cosine
                     >= 0.985 and durations within 25 %; distinct sounds by greedy clustering
  * music bed      = residue level outside events vs voice; tempo (librosa beat tracker),
                     key (Krumhansl chroma profile), 2 s level curve -> swells / drops
"""
import json, sys
import numpy as np
import soundfile as sf

VOC, RES, MOT, OUT = sys.argv[1:5]
SR = 22050
HOP = SR // 100  # 10 ms


def load(p):
    x, sr = sf.read(p, always_2d=True, dtype="float32")
    x = x.mean(axis=1)
    if sr != SR:
        import librosa
        x = librosa.resample(x, orig_sr=sr, target_sr=SR)
    return x


def frames_db(x, win):
    n = len(x) // HOP
    pw = np.convolve(x[:n * HOP] ** 2, np.ones(win) / win, mode="same")[::HOP][:n]
    return 10 * np.log10(pw + 1e-12)


v, r = load(VOC), load(RES)
n = min(len(v), len(r)) // HOP
v, r = v[:n * HOP], r[:n * HOP]
vdb = frames_db(v, HOP * 3)[:n]
rdb = frames_db(r, HOP * 3)[:n]
rdb6 = frames_db(r, HOP * 6)[:n]
dur = n / 100

# rolling 25th percentile over 4 s (computed on a 100 ms grid, interpolated)
grid = np.arange(0, n, 10)
base_g = np.array([np.percentile(rdb[max(0, i - 200):i + 200], 25) for i in grid])
base = np.interp(np.arange(n), grid, base_g)

# voice active level
vp95 = np.percentile(vdb, 95)
v_active = vdb > vp95 - 20
voice_rms = 10 * np.log10(np.mean(10 ** (vdb[v_active] / 10)) + 1e-12)
v_on = np.r_[0, np.diff(vdb)] > 6  # voice onsets (for leakage guard)

# --- STFT for features
import librosa
S = np.abs(librosa.stft(r, n_fft=1024, hop_length=HOP, center=True))[:, :n] ** 2
f = librosa.fft_frequencies(sr=SR, n_fft=1024)
S[f < 30] = 0
tot = S.sum(axis=0) + 1e-12
cen = (S * f[:, None]).sum(axis=0) / tot
mel_fb = librosa.filters.mel(sr=SR, n_fft=1024, n_mels=24)
M = np.log10(mel_fb @ S + 1e-10)


def feats(a, b, pk):
    seg = S[:, a:b + 1]
    E = seg.sum(axis=1) + 1e-12
    w = tot[a:b + 1]
    c = float((cen[a:b + 1] * w).sum() / w.sum())
    t = np.arange(a, b + 1) / 100
    slope = float(np.polyfit(t, cen[a:b + 1], 1, w=np.sqrt(w))[0]) if b - a > 4 else 0.0
    band = seg[(f > 100) & (f < 10000)]
    flat = float(np.median(np.exp(np.mean(np.log(band + 1e-10), axis=0)) / (np.mean(band, axis=0) + 1e-10)))
    lin = 10 ** ((rdb[a:pk + 1] - rdb[pk]) / 20)
    i10 = int(np.argmax(lin >= .1)); i90 = int(np.argmax(lin >= .9))
    fp = M[:, a:min(b + 1, a + 30)].mean(axis=1)
    return dict(centroid=int(c), centroid_slope=int(slope), hf=round(float(E[f > 4000].sum() / E.sum()), 3),
                lf=round(float(E[f < 250].sum() / E.sum()), 3), flat=round(flat, 3),
                attack_ms=int((i90 - i10) * 10)), fp


def classify(e):
    D, A, P = e["dur"], e["attack_ms"], e["peak_pos"]
    if e["kind"] == "riser" or (D >= 1.0 and P > .55 and A > 500):
        return "riser"
    if e.get("src") == "low":
        return "low_hit" if D < .6 else "glow"   # sub boom / low swell
    if e.get("src") == "high" and e["broad"] < .3:
        return "shimmer" if D > .35 else "tick"   # ding / chime / sparkle above the music
    if D < .15:
        return "tick" if e["centroid"] > 1500 else "pop"
    if e["lf"] > .5 and A < 50:
        return "low_hit"
    if e["centroid"] > 3500 and e["hf"] > .45 and D > .3 and A < 30 and e["flat"] < .15:
        return "flash"
    if e["centroid"] > 3500 and D > .3:
        return "shimmer"
    if e["flat"] > .1 and .2 < D < 3.0:
        return "whoosh"
    if D < .45:
        return "pop" if e["centroid"] < 2500 else "tick"
    if A > 80:
        return "glow"
    if A < 20 and e["centroid"] > 2000:
        return "impact"
    return "other"


# --- events = spectral NOVELTY against the music: per mel band, excess over a 4 s rolling
#     median (dB). A music note excites a few harmonic bands; an SFX is either broadband
#     (whoosh / riser / flash / tick / impact), a tonal stack ABOVE the music (> 4.5 kHz:
#     dings, shimmer), or a low swell under it (< 160 Hz: boom / sub whoosh).
from scipy.ndimage import median_filter, uniform_filter1d
NM = 64
fb = librosa.filters.mel(sr=SR, n_fft=1024, n_mels=NM, fmin=40, fmax=11000)
mf = librosa.mel_frequencies(n_mels=NM, fmin=40, fmax=11000)
L = 10 * np.log10(fb @ S + 1e-10)
Lm = median_filter(L, size=(1, 401), mode="nearest")
X = uniform_filter1d(L - Lm, 3, axis=1)
floor = np.percentile(L, 99) - 55
X[L < floor] = 0
broad = (X > 6).mean(axis=0)                     # share of bands 6 dB over the music
hi = X[mf > 4500].clip(0).mean(axis=0)           # tonal/bright excess above the music
lo = X[mf < 160].clip(0).mean(axis=0)            # sub swell excess
mid_narrow = ((X[(mf > 250) & (mf < 4000)] > 8).mean(axis=0))
hot = (broad >= .30) | (hi >= 9) | (lo >= 9)
events = []
i = 0
while i < n:
    if hot[i]:
        j = i
        while j + 1 < n and (hot[j + 1] or (j + 6 < n and hot[j + 1:j + 7].any())):
            j += 1
        if j - i >= 2:
            a = max(0, i - 2)
            b = j
            while b + 1 < n and (broad[b + 1] > .12 or hi[b + 1] > 4 or lo[b + 1] > 4) and b - j < 300:
                b += 1
            sl = slice(a, b + 1)
            src = "broad" if broad[sl].max() >= .30 else ("high" if hi[sl].max() >= 9 else "low")
            events.append(["transient", a, b, src])
        i = j + 1
    else:
        i += 1

# --- risers: smoothed climb >= 9 dB over 0.6-4 s into a peak above the bed, and the climb
#     must be broadband (>= 25 % of bands over the music at the peak) or a sub swell
sm = np.convolve(rdb6, np.ones(15) / 15, mode="same")
for pk in range(60, n - 5):
    if sm[pk] < base[pk] + 6 or sm[pk] != sm[max(0, pk - 40):pk + 40].max():
        continue
    if broad[max(0, pk - 10):pk + 5].max() < .25 and lo[max(0, pk - 10):pk + 5].max() < 9:
        continue
    lo_i = max(0, pk - 400)
    start = lo_i + int(np.argmin(sm[lo_i:pk]))
    if pk - start >= 60 and sm[pk] - sm[start] >= 9:
        seg = sm[start:pk + 1]
        if np.mean(np.diff(seg) > -0.05) > .7:
            b = pk
            while b + 1 < n and sm[b + 1] > base[b + 1] + 3 and b - pk < 150:
                b += 1
            events.append(["riser", start, b, "climb"])

# merge overlaps (riser wins over transients inside its swell)
events.sort(key=lambda e: e[1])
merged = []
for k, a, b, src in events:
    if merged and a <= merged[-1][2]:
        if k == "riser" or merged[-1][0] == "riser":
            merged[-1] = ["riser", min(a, merged[-1][1]), max(b, merged[-1][2]), "climb"]
        else:
            merged[-1][2] = max(b, merged[-1][2])
    else:
        merged.append([k, a, b, src])

mot = json.load(open(MOT))
pc, cuts = mot["panel_changes"], mot["cuts"]
switches = []
for k in range(1, len(mot["runs"])):
    switches.append((mot["runs"][k]["t0"], "to_" + mot["runs"][k]["layout"]))


def layout_at(t):
    for run in mot["runs"]:
        if run["t0"] <= t < run["t0"] + run["dur"]:
            return run["layout"]
    return mot["runs"][-1]["layout"]


def screen(t):
    for ts, what in switches:
        if abs(ts - t) <= .25:
            return f"layout switch {what}"
    for ts in cuts:
        if abs(ts - t) <= .2:
            return "cut/flash"
    if any(abs(ts - t) <= .25 for ts in pc):
        return "panel change (object in/out)"
    return "no visual change"


out_ev, fps = [], []
for k, a, b, src in merged:
    pk = a + int(np.argmax(rdb[a:b + 1]))
    if v_active[pk] and vdb[pk] - rdb[pk] >= 16 and v_on[max(0, pk - 3):pk + 2].any() and k != "riser":
        continue  # demucs bleed of a voice onset
    ft, fp = feats(a, b, pk)
    pkw = slice(max(0, pk - 5), pk + 5)
    p_ev = np.mean(10 ** (rdb[pkw] / 10)) - np.mean(10 ** (base[pkw] / 10))
    lvl = 10 * np.log10(max(p_ev, 1e-12)) - voice_rms
    if lvl < -38:
        continue
    e = dict(t=round(a / 100, 2), peak_t=round(pk / 100, 2), dur=round((b - a + 1) / 100, 2),
             peak_pos=round((pk - a) / max(1, b - a), 2), kind=k, src=src,
             broad=round(float(broad[a:b + 1].max()), 2), level_vs_voice_db=round(float(lvl), 1), **ft)
    e["type"] = classify(e)
    e["layout"] = layout_at(e["t"])
    e["on_screen"] = screen(e["peak_t"] if e["type"] == "riser" else e["t"])
    out_ev.append(e)
    fps.append(fp)

# --- confidence: short broadband hits may be the music's own percussion. Strict SFX =
#     not short, OR short but visually synced (a top-10 % frame change within -0.1..+0.2 s;
#     chance ~20 %). Short + unsynced + on the music's beat/half-beat grid = "music?".
d_all = np.array(mot["d_all"]); fpsm = mot["fps_sampled"]
thr = np.percentile(d_all, 90)
try:
    _, beats = librosa.beat.beat_track(y=r, sr=SR, hop_length=512, units="time")
    beats = np.asarray(beats)
    grid_t = np.sort(np.r_[beats, (beats[1:] + beats[:-1]) / 2]) if len(beats) > 1 else beats
except Exception:
    grid_t = np.array([])
keep_ev, keep_fp = [], []
for e, fp in zip(out_ev, fps):
    tt, w0, w1 = (e["peak_t"], .3, .3) if e["type"] == "riser" else (e["t"], .1, .2)  # risers land ON the hit
    i0, i1 = int((tt - w0) * fpsm), int((tt + w1) * fpsm) + 1
    e["synced"] = bool((d_all[max(0, i0):i1] > thr).any())
    short = e["dur"] < .25 and e["src"] == "broad" and e["type"] in ("pop", "tick", "low_hit")
    on_grid = bool(len(grid_t) and np.abs(grid_t - e["t"]).min() < .045)
    e["on_beat_grid"] = on_grid
    e["conf"] = "sfx" if (not short or e["synced"]) else ("music?" if on_grid else "uncertain")
    keep_ev.append(e); keep_fp.append(fp)
all_ev = out_ev
out_ev = [e for e in keep_ev if e["conf"] == "sfx"]
fps = [fp for e, fp in zip(keep_ev, keep_fp) if e["conf"] == "sfx"]
sync_rate = float(np.mean([e["synced"] for e in out_ev])) if out_ev else 0
chance = float(np.mean(np.convolve(d_all > thr, np.ones(4), "same") > 0))

# repetition
for i, e in enumerate(out_ev):
    e["same_as_prev"] = False
    if i:
        a, b = fps[i] - fps[i].mean(), fps[i - 1] - fps[i - 1].mean()
        cs = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        d0, d1 = e["dur"], out_ev[i - 1]["dur"]
        e["sim_prev"] = round(cs, 3)
        e["same_as_prev"] = bool(cs >= .985 and abs(d0 - d1) <= .25 * max(d0, d1))
clusters = []
for i, fp in enumerate(fps):
    a = fp - fp.mean()
    for c in clusters:
        b = c["fp"]
        if a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9) >= .985:
            c["n"] += 1; out_ev[i]["cluster"] = c["id"]; break
    else:
        clusters.append({"id": len(clusters), "fp": a, "n": 1}); out_ev[i]["cluster"] = len(clusters) - 1

# music bed
ev_mask = np.zeros(n, bool)
for e in out_ev:
    ev_mask[int(e["t"] * 100):int((e["t"] + e["dur"]) * 100) + 1] = True
bed = rdb[~ev_mask] if (~ev_mask).sum() > 100 else rdb
bed_rms = 10 * np.log10(np.mean(10 ** (bed / 10)) + 1e-12)
curve = [round(float(10 * np.log10(np.mean(10 ** (rdb[i:i + 200][~ev_mask[i:i + 200]] / 10)) + 1e-12)) - voice_rms, 1)
         if (~ev_mask[i:i + 200]).sum() > 20 else None for i in range(0, n, 200)]
med = np.median([c for c in curve if c is not None]) if any(c is not None for c in curve) else -60
swells = [i * 2 for i, c in enumerate(curve) if c is not None and c > med + 4]
drops = [i * 2 for i, c in enumerate(curve) if c is not None and c < med - 6]
has_bed = bool(bed_rms - voice_rms > -40 and np.mean(rdb[~ev_mask] > voice_rms - 45) > .6)
tempo, key, mode = None, None, None
if has_bed:
    yb = r.copy()
    try:
        tempo = float(np.atleast_1d(librosa.beat.beat_track(y=yb, sr=SR, hop_length=512)[0])[0])
        ch = librosa.feature.chroma_cqt(y=yb, sr=SR, hop_length=2048).mean(axis=1)
        maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        names = "C C# D D# E F F# G G# A A# B".split()
        best = max(((np.corrcoef(np.roll(p, s), ch)[0, 1], names[s], m) for s in range(12)
                    for p, m in ((maj, "major"), (mnr, "minor"))))
        key, mode = best[1], best[2]
    except Exception as ex:  # noqa
        print("music feature error", ex)
    cen_bed = float(np.median(cen[~ev_mask]))
else:
    cen_bed = None

types = {}
for e in out_ev:
    types[e["type"]] = types.get(e["type"], 0) + 1
gaps = np.diff([e["t"] for e in out_ev]) if len(out_ev) > 1 else np.array([])
res = dict(
    duration=round(dur, 2), voice_active_rms_db=round(float(voice_rms), 1),
    n_events=len(out_ev), sfx_per_min=round(len(out_ev) / dur * 60, 1), types=types,
    risers=types.get("riser", 0),
    median_gap_s=round(float(np.median(gaps)), 2) if len(gaps) else None,
    min_gap_s=round(float(gaps.min()), 2) if len(gaps) else None,
    level_vs_voice_db_median=round(float(np.median([e["level_vs_voice_db"] for e in out_ev])), 1) if out_ev else None,
    level_by_type={t: round(float(np.median([e["level_vs_voice_db"] for e in out_ev if e["type"] == t])), 1) for t in types},
    back_to_back_same=sum(e["same_as_prev"] for e in out_ev),
    distinct_sounds=len(clusters),
    on_screen={s: sum(e["on_screen"] == s for e in out_ev) for s in sorted({e["on_screen"] for e in out_ev})},
    music=dict(has_bed=has_bed, bed_vs_voice_db=round(float(bed_rms - voice_rms), 1), tempo_bpm=round(tempo, 1) if tempo else None,
               key=f"{key} {mode}" if key else None, bed_centroid_hz=int(cen_bed) if cen_bed else None,
               curve_2s_vs_voice_db=curve, swells_s=swells, drops_s=drops),
    visual_sync_rate=round(sync_rate, 2), visual_sync_chance=round(chance, 2),
    loose=dict(n=len(all_ev), per_min=round(len(all_ev) / dur * 60, 1),
               music_like=sum(e["conf"] == "music?" for e in all_ev), uncertain=sum(e["conf"] == "uncertain" for e in all_ev)),
    events=out_ev,
    excluded=[e for e in all_ev if e["conf"] != "sfx"],
)
json.dump(res, open(OUT, "w"), indent=1)
print(f"{OUT.split('/')[-1]}: {len(out_ev)} ev ({res['sfx_per_min']}/min) {types} bed {res['music']['bed_vs_voice_db']} dB "
      f"tempo {res['music']['tempo_bpm']} key {res['music']['key']} b2b-same {res['back_to_back_same']} sync {sync_rate:.2f}/{chance:.2f} loose {len(all_ev)}")
