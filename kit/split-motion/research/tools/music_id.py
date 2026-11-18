#!/usr/bin/env python3
"""Try to identify the music bed of reference reels (free Shazam endpoint via shazamio).

usage: python3 -I music_id.py OUT.json STEM_DIR ID [ID ...]
  STEM_DIR/<id>/no_vocals.wav (demucs) — the voice is removed so the matcher hears the music.
  Queries 4 windows of 14 s (10/35/60/85 % of the reel), loudness-normalised, and the
  original mix's first 14 s as a fallback. Nothing is downloaded or stored but the metadata.
"""
import asyncio, json, os, subprocess, sys, tempfile

OUT, STEMS, IDS = sys.argv[1], sys.argv[2], sys.argv[3:]


async def rec(shazam, path):
    for _ in range(2):
        try:
            r = await shazam.recognize(path)
            t = r.get("track")
            if t:
                return {"title": t.get("title"), "artist": t.get("subtitle"), "shazam_url": t.get("url"),
                        "isrc": t.get("isrc"), "genre": (t.get("genres") or {}).get("primary")}
            return None
        except Exception as ex:  # noqa
            await asyncio.sleep(2)
    return None


async def main():
    from shazamio import Shazam
    sh = Shazam()
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for i in IDS:
        src = os.path.join(STEMS, i, "no_vocals.wav")
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                   capture_output=True, text=True).stdout)
        hits = []
        with tempfile.TemporaryDirectory() as td:
            for frac in (.10, .35, .60, .85):
                t0 = max(0, min(dur - 14, dur * frac))
                p = os.path.join(td, f"w{int(frac*100)}.wav")
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.2f}", "-t", "14", "-i", src, "-af",
                                "loudnorm=I=-14:TP=-1", "-ar", "44100", "-ac", "1", p], check=True)
                h = await rec(sh, p)
                hits.append({"t0": round(t0, 1), "match": h})
                await asyncio.sleep(1.5)
        found = [h["match"] for h in hits if h["match"]]
        res[i] = {"windows": hits, "best": max(found, key=lambda m: sum(f["title"] == m["title"] for f in found)) if found else None}
        print(i, "->", res[i]["best"]["title"] + " — " + res[i]["best"]["artist"] if found else "no match", flush=True)
        json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)

asyncio.run(main())
