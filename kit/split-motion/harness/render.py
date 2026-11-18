#!/usr/bin/env python3
"""Chunked parallel render: split the timeline into N frame-exact chunks, render them
concurrently with HyperFrames, crop each to 1080x1920 as it finishes, concat losslessly, mux audio.

    render(project_dir, make_chunk_html(off, dur) -> str, total, audio_wav, out_mp4, n=None, workers=1)

Why chunks: one `hyperframes render -w N` already uses N Chrome workers, but its capture,
encode and the final crop/re-encode are serial stages. N independent renders keep every core
busy through all stages, and the crop of chunk k overlaps the render of chunk k+1.
Chunk boundaries sit on the 1/30 s frame grid, so the concat is exact (no dup/drop).
"""
import os, subprocess, time
from concurrent.futures import ThreadPoolExecutor

FPS = 30
HF = ["npx", "--yes", "hyperframes@0.6.49"]


def plan_chunks(total, n, cost=None):
    """frame-exact chunks of equal estimated COST (cost(t) per frame: 3D ~3x, <video> frames ~1.6x)."""
    F = int(round(total * FPS))
    w = [cost(f / FPS) if cost else 1.0 for f in range(F)]
    tot, acc, cuts, k = sum(w), 0.0, [0], 1
    for f in range(F):
        acc += w[f]
        if k < n and acc >= tot * k / n:
            cuts.append(f + 1)
            k += 1
    cuts = sorted(set(cuts + [F]))
    return [(cuts[i] / FPS, (cuts[i + 1] - cuts[i]) / FPS, cuts[i + 1] - cuts[i]) for i in range(len(cuts) - 1)]


def render(proj, make_html, total, audio, out, n=None, workers=1, crf=18, log=print, card_from=None, split_iv=(), cost=None):
    """card_from = base video path: during split_iv (reel seconds) its card band y 1370-1920 is
    overlaid on the HTML render (the page then needs no <video> there: ~45 % faster frames)."""
    n = n or max(1, (os.cpu_count() or 4))
    chunks = plan_chunks(total, n, cost)
    n = len(chunks)
    rd = os.path.join(proj, "renders", "_chunks")
    os.makedirs(rd, exist_ok=True)
    t0 = time.time()
    times = {}

    def one(k):
        off, dur, frames = chunks[k]
        name = f"_chunk{k:02d}.html"
        open(os.path.join(proj, name), "w").write(make_html(off, dur))
        raw = os.path.join(rd, f"raw{k:02d}.mp4")
        a = time.time()
        r = subprocess.run(HF + ["render", "-c", name, "-o", raw, "-w", str(workers), "--quiet", "--crf", "16"],
                           cwd=proj, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"chunk {k} render failed: {r.stdout[-800:]} {r.stderr[-800:]}")
        b = time.time()
        crop = os.path.join(rd, f"c{k:02d}.mp4")
        iv = [(max(a_, off) - off, min(b_, off + dur) - off) for a_, b_ in split_iv if min(b_, off + dur) - max(a_, off) > 0]
        if card_from and iv:
            en = "+".join(f"between(t,{a_:.4f},{b_ - .0005:.4f})" for a_, b_ in iv)
            fc = (f"[1:v]crop=1080:550:0:1370,setpts=PTS-STARTPTS[card];[0:v]setpts=PTS-STARTPTS[h];"
                  f"[h][card]overlay=0:1370:enable='{en}',crop=1080:1920:0:0[v]")
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", raw, "-ss", f"{off:.4f}", "-t", f"{dur + .1:.4f}", "-i", card_from,
                   "-filter_complex", fc, "-map", "[v]"]
        else:
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf", "crop=1080:1920:0:0"]
        subprocess.run(cmd + ["-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                              "-pix_fmt", "yuv420p", "-g", "60", "-threads", "2", crop], check=True)
        os.remove(raw)
        os.remove(os.path.join(proj, name))
        times[k] = (round(b - a, 1), round(time.time() - b, 1))
        log(f"  chunk {k}: {frames} frames render {times[k][0]} s, crop {times[k][1]} s")
        return crop

    with ThreadPoolExecutor(n) as ex:
        parts = list(ex.map(one, range(n)))
    lst = os.path.join(rd, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    for p in parts + [lst]:
        os.remove(p)
    os.rmdir(rd)
    return dict(chunks=n, workers_per_chunk=workers, wall_s=round(time.time() - t0, 1), per_chunk=times)
