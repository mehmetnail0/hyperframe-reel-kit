#!/usr/bin/env python3
"""Ingest: ONE pass over the raw clip, three jobs in parallel.

  transcribe(raw, out)   faster-whisper (word timestamps, VAD) on 16 kHz mono  -> words.json
  vision(raw, out)       ONE decode of the video at 5 fps / 320 px: shot boundaries (luma-histogram
                         jump) + Haar face boxes per shot (largest face, median over the shot)
                         -> shots.json ; also writes a 2 fps contact sheet for the planner/QC
  energy(raw, out)       10 ms RMS envelope (dBFS) of the speech -> energy.npy (cut points snap
                         to dips in it)

usage: python3 -I ingest.py RAW.mp4 WORKDIR [--whisper small.en] [--lang en]
All three run concurrently (ProcessPool); timings are returned / printed as JSON.
"""
import json, os, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

FFM = ["ffmpeg", "-v", "error", "-y"]


def probe(raw):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", raw],
                                  capture_output=True, text=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return dict(w=int(v["width"]), h=int(v["height"]), fps=float(num) / float(den), dur=float(j["format"]["duration"]))


def transcribe(raw, work, model="small.en", lang="en", threads=2):
    t0 = time.time()
    wav = os.path.join(work, "a16.wav")
    subprocess.run(FFM + ["-i", raw, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=threads)
    import soundfile as sf
    audio = sf.read(wav, dtype="float32")[0]  # numpy in: avoids faster-whisper's PyAV decoder
    segs, info = m.transcribe(audio, language=None if lang == "auto" else lang,
                              word_timestamps=True, vad_filter=True, beam_size=1, condition_on_previous_text=False)
    words, sents = [], []
    for s in segs:
        ws = [dict(w=w.word.strip(), t=round(w.start, 3), e=round(w.end, 3), p=round(w.probability, 2))
              for w in (s.words or []) if w.word.strip()]
        if ws:
            sents.append(dict(t=round(s.start, 3), e=round(s.end, 3), text=s.text.strip(), i0=len(words), i1=len(words) + len(ws)))
            words += ws
    json.dump(dict(words=words, segments=sents, lang=info.language), open(os.path.join(work, "words.json"), "w"), indent=0)
    return dict(step="transcribe", s=round(time.time() - t0, 1), words=len(words))


def vision(raw, work, fps=5, width=320):
    t0 = time.time()
    import cv2
    pr = probe(raw)
    h = int(round(pr["h"] * width / pr["w"] / 2) * 2)
    # one decode, two outputs: analysis frames (raw gray) and a 2 fps sheet for the planner
    sheet = os.path.join(work, "sheet_raw.jpg")
    # sources taller than 1440 px (4K) also get a 1080p/30 fps H.264 mezzanine from the SAME decode:
    # the split-card segments are cut from it (they are downscaled anyway), only punch-ins read the original
    big = pr["h"] > 1440 or pr["fps"] > 31
    ph = 1080 if pr["h"] > 1440 else pr["h"]
    pw = int(round(pr["w"] * ph / pr["h"] / 2) * 2)
    fc = (f"[0:v]split={3 if big else 2}[v0][v1]{'[v2]' if big else ''};[v0]fps={fps},scale={width}:{h},format=gray[g];"
          f"[v1]fps=1,scale=160:-2,tile=12x8[s]" + (f";[v2]fps=30,scale={pw}:{ph}:flags=bicubic[p]" if big else ""))
    cmd = FFM + ["-threads", "0", "-i", raw, "-an", "-filter_complex", fc,
                 "-map", "[g]", "-f", "rawvideo", "pipe:1", "-map", "[s]", "-frames:v", "1", sheet]
    if big:
        cmd += ["-map", "[p]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "17", "-g", "15", "-pix_fmt", "yuv420p",
                os.path.join(work, "proxy.mp4")]
    raw_bytes = subprocess.run(cmd, capture_output=True, check=True).stdout
    fr = np.frombuffer(raw_bytes, np.uint8).reshape(-1, h, width)
    n = len(fr)
    hist = np.array([np.bincount(f.ravel() // 8, minlength=32) / f.size for f in fr])
    jump = np.r_[0, np.abs(np.diff(hist, axis=0)).sum(axis=1)]
    cuts = [0] + [i for i in range(1, n) if jump[i] > 0.35 and jump[i] == jump[max(0, i - 2):i + 3].max()]
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    shots = []
    for k, a in enumerate(cuts):
        b = cuts[k + 1] if k + 1 < len(cuts) else n
        boxes = []
        for i in range(a, b, max(1, (b - a) // 6)):
            fs = casc.detectMultiScale(fr[i], 1.1, 5, minSize=(width // 20, width // 20))
            if len(fs):
                x, y, w, hh = max(fs, key=lambda f: f[2] * f[3])
                boxes.append((x, y, w, hh))
        sx = pr["w"] / width
        face = None
        if boxes:
            bx = np.median(np.array(boxes), axis=0) * sx
            face = dict(cx=round(bx[0] + bx[2] / 2), cy=round(bx[1] + bx[3] / 2), size=round(bx[2]))
        shots.append(dict(t0=round(a / fps, 2), t1=round(b / fps, 2), face=face,
                          nfaces=int(np.median([1 if boxes else 0])) if boxes else 0))
    proxy = dict(path=os.path.join(work, "proxy.mp4"), w=pw, h=ph) if big else None
    json.dump(dict(src=pr, shots=shots, proxy=proxy), open(os.path.join(work, "shots.json"), "w"), indent=1)
    return dict(step="vision", s=round(time.time() - t0, 1), shots=len(shots), frames=n)


def energy(raw, work):
    t0 = time.time()
    pcm = subprocess.run(FFM + ["-i", raw, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    hop = 160
    n = len(x) // hop
    rms = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-10)
    np.save(os.path.join(work, "energy.npy"), (20 * np.log10(rms)).astype(np.float32))
    return dict(step="energy", s=round(time.time() - t0, 1))


def run(raw, work, model="small.en", lang="en"):
    os.makedirs(work, exist_ok=True)
    t0 = time.time()
    with ProcessPoolExecutor(3) as ex:
        fs = [ex.submit(transcribe, raw, work, model, lang, max(1, (os.cpu_count() or 4) - 2)),
              ex.submit(vision, raw, work), ex.submit(energy, raw, work)]
        res = [f.result() for f in fs]
    return dict(step="ingest", s=round(time.time() - t0, 1), parts=res)


if __name__ == "__main__":
    a = sys.argv[1:]
    model = a[a.index("--whisper") + 1] if "--whisper" in a else "small.en"
    lang = a[a.index("--lang") + 1] if "--lang" in a else "en"
    print(json.dumps(run(a[0], a[1], model, lang)))
