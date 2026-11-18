#!/usr/bin/env python3
"""Story cut + speaker video builder for split-motion-dai.

usage: python3 -I scripts/edit.py RAW.mp4 WORKDIR

 1. KEEP ranges (original-clip seconds) chosen from the whisper.cpp transcript.
 2. Internal silences (ffmpeg silencedetect) are tightened to ~0.2 s.
 3. Every cut point is snapped to the quietest 10 ms window within +-0.12 s
    (so no word is clipped) and then to the 1/30 s frame grid.
 4. Writes  data/edl.json        (segments: orig in/out -> new start)
            (caption word timings come from scripts/captions.py)
            WORKDIR/speech.wav   (cut speech, 48 kHz stereo, 8 ms fades per cut)
            WORKDIR/base.mp4     (1080x2040 video-only: split layout = speaker crop
                                  in y 1150..1920, top black for the HTML panel;
                                  punch-in = full 9:16 crop from the 4K source)
"""
import json, math, os, subprocess, sys, wave, array

RAW, WORK = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.makedirs(WORK, exist_ok=True)
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
FPS = 30

# ---- 1. story cut (original clip time) -------------------------------------
KEEP = [  # every boundary sits inside a measured energy dip (>=30 ms below -42 dBFS)
    (7.73, 14.06),   # instant gratification ... money or attention, followers.
    (14.67, 17.85),  # People just want it now. And when they don't get it now, they stop.
    (18.80, 40.03),  # people ask me "can you shout me out?" I say no ... you don't have the catalog.
    (40.95, 62.47),  # keep dropping, be consistent ... fireworks happen ... that level of opportunity
    (65.41, 81.73),  # If somebody say "hey, I got a contract" ... lawyer? ... step zero ... step A.
]
# silences to keep a little longer (dramatic beats): start-of-silence -> kept length
HOLD = {47.196: 0.42, 77.9604: 0.38, 22.0169: 0.26}

# camera cuts in the raw multicam (ffmpeg scene detect) and crops in 4K px
CAMS = [(0, "S"), (4.688, "H"), (10.188, "W"), (18.188, "S"), (25.188, "H"),
        (26.688, "S"), (48.688, "H"), (50.188, "S"), (66.188, "W"), (75.188, "S"),
        (81.688, "H")]
CROP = {  # w, h, x, y   (aspect 1080:770). *_z = tighter alternate for jump cuts
    "S": (1960, 1397, 920, 120), "S_z": (1720, 1226, 1020, 190),
    "H": (1960, 1397, 670, 0),   "H_z": (1720, 1226, 790, 60),
    "W": (1360, 969, 2440, 170), "W_z": (1220, 870, 2520, 210),
}
TAIL = (81.80, 83.80)              # recap tail shot (video only)
PUNCH_CROP = (1215, 2160, 1272, 0)   # 9:16 on the main speaker cam, sharp
# full-screen punch-ins (original time, must sit inside an "S" camera range)
PUNCH = [(21.37, 22.95), (31.03, 33.50), (37.45, 40.03), (51.00, 52.30),
         (58.40, 60.82)]


def run(cmd):
    subprocess.run(cmd, check=True)


# ---- 2. audio analysis -------------------------------------------------------
pcm = os.path.join(WORK, "a16.wav")
run(["ffmpeg", "-v", "error", "-y", "-i", RAW, "-ac", "1", "-ar", "16000", pcm])
w = wave.open(pcm); sr = w.getframerate()
samples = array.array("h", w.readframes(w.getnframes())); w.close()
win = sr // 100  # 10 ms
rms = []
for i in range(0, len(samples) - win, win):
    s = samples[i:i + win]
    rms.append(math.sqrt(sum(v * v for v in s) / win))


def snap(t, rad=0.04):
    i0, i1 = max(0, int((t - rad) * 100)), min(len(rms) - 1, int((t + rad) * 100))
    best = min(range(i0, i1 + 1), key=lambda i: (rms[i], abs(i / 100 - t)))
    return best / 100 + 0.005


def grid(t):
    return round(t * FPS) / FPS


out = subprocess.run(["ffmpeg", "-i", pcm, "-af", "silencedetect=noise=-32dB:d=0.35",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
sil, st = [], None
for line in out.splitlines():
    if "silence_start" in line:
        st = float(line.split("silence_start:")[1])
    elif "silence_end" in line and st is not None:
        sil.append((st, float(line.split("silence_end:")[1].split("|")[0]))); st = None

# ---- 3. build segment list (tighten silences, snap) --------------------------
segs = []
for a, b in KEEP:
    a, b = grid(snap(a)), grid(snap(b))
    cur = a
    for s, e in sil:
        if s > a + 0.05 and e < b - 0.05:
            keep = HOLD.get(round(s, 4), 0.2)
            if e - s <= keep + 0.08:
                continue
            c0, c1 = grid(s + keep / 2), grid(e - keep / 2)
            segs.append([cur, c0]); cur = c1
    segs.append([cur, b])

t = 0.0
edl = []
for a, b in segs:
    edl.append({"in": round(a, 4), "out": round(b, 4), "start": round(t, 4)})
    t += b - a
TOTAL = round(t, 4)


def remap(x):
    for s in edl:
        if s["in"] - 1e-6 <= x <= s["out"] + 1e-6:
            return s["start"] + x - s["in"]
    return None


# words: whisper.cpp -ojf -ml 1 segments
wj = json.load(open(os.path.join(HERE, "whisper_words.json")))
FIX = {"Z.": "zero."}
words = []
for seg in wj["transcription"]:
    txt = seg["text"].strip()
    if not txt:
        continue
    a, b = seg["offsets"]["from"] / 1000, seg["offsets"]["to"] / 1000
    mid = remap(min(a + 0.06, b))
    if mid is None:
        continue
    na = remap(a)
    if na is None:
        na = mid - 0.06
    words.append({"w": FIX.get(txt, txt), "t": round(na, 3), "o": round(a, 3)})
for i, wd in enumerate(words):
    nxt = words[i + 1]["t"] if i + 1 < len(words) else TOTAL
    wd["d"] = round(max(0.12, min(nxt - wd["t"], 1.2)), 3)

punch_new = []
for a, b in PUNCH:
    na, nb = remap(grid(a) if remap(grid(a)) is not None else a), remap(b)
    if na is None:
        na = remap(min(s["in"] for s in edl if s["in"] >= a))
    if nb is None:
        nb = remap(max(s["out"] for s in edl if s["out"] <= b))
    punch_new.append([round(grid(na), 4), round(grid(nb), 4)])
# merge adjacent punches
merged = []
for p in punch_new:
    if merged and p[0] - merged[-1][1] < 0.05:
        merged[-1][1] = p[1]
    else:
        merged.append(p)
punch_new = merged

json.dump({"total": TOTAL, "video_total": round(TOTAL + TAIL[1] - TAIL[0], 4),
           "segments": edl, "punch": punch_new},
          open(os.path.join(ROOT, "data", "edl.json"), "w"), indent=1)
json.dump(words, open(os.path.join(WORK, "words_remap_rough.json"), "w"), indent=0)
print("segments", len(edl), "total", TOTAL, "punch", punch_new)

# ---- 4. speech audio ---------------------------------------------------------
parts, labels = [], []
for i, s in enumerate(edl):
    d = s["out"] - s["in"]
    parts.append(f"[0:a]atrim={s['in']:.4f}:{s['out']:.4f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d=0.008,afade=t=out:st={d - 0.008:.4f}:d=0.008[a{i}]")
    labels.append(f"[a{i}]")
fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(edl)}:v=0:a=1,aresample=48000[out]"
run(["ffmpeg", "-v", "error", "-y", "-i", RAW, "-filter_complex", fc, "-map", "[out]",
     "-ac", "2", "-ar", "48000", os.path.join(WORK, "speech.wav")])

# ---- 5. speaker video (per sub-segment, then concat) -------------------------
def cam_at(x):
    c = CAMS[0][1]
    for t0, name in CAMS:
        if x + 1e-6 >= t0:
            c = name
    return c


def cut_points(a, b):
    pts = [a]
    for t0, _ in CAMS:
        tc = math.ceil(t0 * FPS) / FPS
        if a < tc < b:
            pts.append(tc)
    for pa, pb in PUNCH:
        for x in (grid(pa), grid(pb)):
            if a < x < b:
                pts.append(x)
    pts.append(b)
    return sorted(set(round(p, 4) for p in pts))


def in_punch(x):
    return any(grid(pa) - 1e-6 <= x < grid(pb) - 1e-6 for pa, pb in PUNCH)


segdir = os.path.join(WORK, "vseg"); os.makedirs(segdir, exist_ok=True)
lst, idx, prev_cam, zoom = [], 0, None, False
for s in edl:
    pts = cut_points(s["in"], s["out"])
    for a, b in zip(pts[:-1], pts[1:]):
        if b - a < 0.5 / FPS:
            continue
        cam = cam_at(a + 0.001)
        if in_punch(a + 0.001) and cam == "S":
            cw, ch, cx, cy = PUNCH_CROP
            vf = (f"crop={cw}:{ch}:{cx}:{cy},scale=1080:1920:flags=lanczos,"
                  f"pad=1080:2040:0:0:black")
        else:
            # same camera continuing across a story cut = jump cut -> alternate zoom
            if cam == prev_cam and a in [x["in"] for x in edl]:
                zoom = not zoom
            elif cam != prev_cam:
                zoom = False
            cw, ch, cx, cy = CROP[cam + ("_z" if zoom else "")]
            vf = (f"crop={cw}:{ch}:{cx}:{cy},scale=1080:770:flags=lanczos,"
                  f"pad=1080:2040:0:1150:black")
        prev_cam = cam
        n = round((b - a) * FPS)
        f = os.path.join(segdir, f"s{idx:03d}.mp4"); idx += 1
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", RAW, "-an",
             "-vf", vf + f",fps={FPS}", "-frames:v", str(n),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
             "-pix_fmt", "yuvj420p", "-color_range", "pc", f])
        lst.append(f"file '{f}'")
# recap tail: 2 s of the next (reaction) shot, video only - audio stays SFX-only
TA, TB = TAIL
cw, ch, cx, cy = CROP[cam_at(TA + 0.001)]
f = os.path.join(segdir, f"s{idx:03d}.mp4")
run(["ffmpeg", "-v", "error", "-y", "-ss", f"{TA:.4f}", "-i", RAW, "-an", "-vf",
     f"crop={cw}:{ch}:{cx}:{cy},scale=1080:770:flags=lanczos,pad=1080:2040:0:1150:black,fps={FPS}",
     "-frames:v", str(round((TB - TA) * FPS)), "-c:v", "libx264", "-preset", "veryfast",
     "-crf", "14", "-pix_fmt", "yuvj420p", "-color_range", "pc", f])
lst.append(f"file '{f}'")
open(os.path.join(WORK, "vseg.txt"), "w").write("\n".join(lst) + "\n")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
     os.path.join(WORK, "vseg.txt"), "-c:v", "libx264", "-profile:v", "high",
     "-pix_fmt", "yuvj420p", "-color_range", "pc", "-r", str(FPS), "-g", "15",
     "-keyint_min", "15", "-crf", "19", "-preset", "slow", "-movflags", "+faststart",
     os.path.join(WORK, "base.mp4")])
print("done", TOTAL)
