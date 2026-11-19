#!/usr/bin/env python3
"""Soft SFX pre-mix from the member's OWN library (no synthesized sound).

usage:
  python3 -I sfx_mix.py gain  MAP.json LIBRARY_DIR SPEECH.wav     # measure + write gain_db into MAP
  python3 -I sfx_mix.py mix   MAP.json LIBRARY_DIR SPEECH.wav OUT.wav TOTAL_SECONDS [--music BED.wav]
  (sounds carrying "max_m" from sfx/palette.json are not re-measured: one voice measurement total)

MAP.json (commit this, never the library):
  "sounds": { name: { "file": path inside LIBRARY_DIR, "peak_ms": where the sound's
               envelope peaks, "fade_in_ms": 5-20, "lowpass": Hz or 0,
               "under_voice_db": 14-20, "gain_db": written by `gain` } }
  "events": [ { "t": seconds, "sound": name, "align": "start"|"peak", "trim_db": 0, "why": "..." } ]

  align "peak" = the sound's peak lands on t (a glow swell peaks when the object
  lands; a whoosh peaks mid fly-in; a riser peaks on the reveal). If that puts the
  start before 0 the head is trimmed.

Gain: the processed sound's max momentary loudness (400 ms) is set `under_voice_db`
below the speech's integrated loudness. The voice stays RAW: the final pass is one
linear gain to -14 LUFS integrated + a peak limiter, verified true peak <= -1 dBTP.
"""
import json, os, re, subprocess, sys

FFM = ["ffmpeg", "-hide_banner", "-nostats"]


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace").stderr


def chain(s, head=0.0):
    f = [f"atrim=start={head:.4f}", "asetpts=PTS-STARTPTS", "aresample=48000",
         "aformat=sample_fmts=fltp:channel_layouts=stereo"]
    if s.get("lowpass"):
        f.append(f"lowpass=f={s['lowpass']}:p=2")
    f.append(f"afade=t=in:d={s.get('fade_in_ms', 10) / 1000:.3f}")
    return ",".join(f)


def loud(path, af):
    r = sh(FFM + ["-i", path, "-af", af + ",ebur128=peak=true", "-f", "null", "-"])
    ms = [float(x) for x in re.findall(r"M:\s*(-?[\d.]+)", r)]
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return (max(ms) if ms else -70.0), (float(i[-1]) if i else -70.0), (float(tp[-1]) if tp else 0.0)


def gain(mp, lib, speech):
    m = json.load(open(mp))
    _, vI, _ = loud(speech, "anull")
    m["voice_lufs_raw"] = vI
    for name, s in m["sounds"].items():
        mmax, _, _ = loud(os.path.join(lib, s["file"]), chain(s) + ",apad=pad_dur=0.6")  # pad: M needs 400 ms
        s["gain_db"] = round(vI - s["under_voice_db"] - mmax, 1)
        print(f"{name:14s} maxM {mmax:6.1f} -> gain {s['gain_db']:+5.1f} dB  ({s['file']})")
    json.dump(m, open(mp, "w"), indent=1, ensure_ascii=False)


def mix(mp, lib, speech, out, total, music=None, music_db=-17.0):
    m = json.load(open(mp))
    vI = None
    if any("gain_db" not in s for s in m["sounds"].values()):
        _, vI, _ = loud(speech, "anull")  # one measurement; per-file max_m comes cached from the palette
        for s in m["sounds"].values():
            if "gain_db" not in s:
                mm = s.get("max_m")
                if mm is None:
                    mm, _, _ = loud(os.path.join(lib, s["file"]), chain(s) + ",apad=pad_dur=0.6")
                s["gain_db"] = round(vI - s["under_voice_db"] - mm, 1)
    inputs, fl, labels = ["-i", speech], [f"[0:a]apad=whole_dur={total:.3f},atrim=0:{total:.3f}[sp]"], ["[sp]"]
    for k, e in enumerate(sorted(m["events"], key=lambda e: e["t"])):
        s = m["sounds"][e["sound"]]
        start = e["t"] - (s.get("peak_ms", 0) / 1000 if e.get("align") == "peak" else 0)
        head = max(0.0, -start)
        start = max(0.0, start)
        g = s["gain_db"] + e.get("trim_db", 0)
        inputs += ["-i", os.path.join(lib, s["file"])]
        ms = int(round(start * 1000))
        fl.append(f"[{k + 1}:a]{chain(s, head)},volume={g:.1f}dB,adelay={ms}|{ms}[s{k}]")
        labels.append(f"[s{k}]")
    if music:  # licensed bed: level music_db under the voice (Kallaway median -17), ducked by the speech
        if vI is None:
            _, vI, _ = loud(speech, "anull")
        _, mI, _ = loud(music, "anull")
        k = len(inputs) // 2
        inputs += ["-stream_loop", "-1", "-i", music]
        fl.append(f"[{k}:a]atrim=0:{total:.3f},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                  f"volume={vI + music_db - mI:.1f}dB,afade=t=in:d=0.6,afade=t=out:st={max(0, total - 1.2):.2f}:d=1.2[bed]")
        fl[0] = fl[0].replace("[sp]", "[sp0]") + ";[sp0]asplit=2[sp][key]"
        fl.append("[bed][key]sidechaincompress=threshold=0.05:ratio=3:attack=20:release=350[mus]")
        labels.append("[mus]")
    fc = ";".join(fl) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,atrim=0:{total:.3f}[m]"
    pre = out + ".pre.wav"
    subprocess.run(FFM + ["-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[m]",
                          "-ar", "48000", "-ac", "2", "-c:a", "pcm_f32le", pre], check=True)
    _, I, _ = loud(pre, "anull")
    g = -14.0 - I
    lim = 0.83
    for _ in range(6):  # linear gain + limiter; nudge gain to I = -14 +-0.2 and the ceiling to TP <= -1
        subprocess.run(FFM + ["-v", "error", "-y", "-i", pre, "-af",
                              f"volume={g:.2f}dB,alimiter=limit={lim:.3f}:attack=1:release=60:level=disabled",
                              "-ar", "48000", "-ac", "2", out], check=True)
        _, I2, tp = loud(out, "anull")
        if abs(I2 + 14) <= .2 and tp <= -1.0:
            break
        g += (-14.0 - I2)
        if tp > -1.0:  # inter-sample overs: lower the limiter ceiling by the overshoot (+0.3 dB margin)
            lim *= 10 ** ((-1.3 - tp) / 20)
    os.remove(pre)
    print(f"mix: {len(labels) - 1} sfx events, I {I2:.1f} LUFS, true peak {tp:.1f} dBTP -> {out}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gain":
        gain(a[1], a[2], a[3])
    else:
        mus = a[a.index("--music") + 1] if "--music" in a else None
        mix(a[1], a[2], a[3], a[4], float(a[5]), mus)
