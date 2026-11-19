# split-motion-margot — harness proof #2 (different source, different motions)

## v2 — round 2 (owner feedback), `renders/FINAL-v2.mp4`

Same source, re-planned fresh with the round-2 rules (stillness by default, no caption echo,
tall speaker card, device clipping, hitch fixes). Fresh run: **279.7 s (4.7 min)** including render.
Jump detector: round-1 render 6 flagged frames (4 snaps, 1 pop, 1 repeat) + 5 duplicated frames in
its base video → round 2: **0** flagged, **0** card repeats; ambient motion 15.5 % of hold frames in the final render
(round 1: 54 %). `FINAL-v2.mp4` is the look-and-fix re-render from the same plan (shine envelope fix).
Sheet: `renders/FINAL-v2-sheet.jpg`. Round 1 below is kept for comparison (`renders/FINAL.mp4`).

## v1 — round 1

Second end-to-end run of `kit/split-motion/harness/run.py`, on a **different** CC-BY
talking head than proof v3: a single-camera 1080p H.264 interview (Margot Comstock,
co-founder of *Softalk* magazine, Apple II Reunion 2015) instead of the 4K multicam podcast.
The model planned the story ("The Magazine That Couldn't Favor": one issue → five years,
$2 → $5 per copy, the little pamphlet, three-way partners, the one rule: no favoring,
Beagle Bros) with the memory of v3 in its prompt.

**Credit:** Footage: "Margot Comstock Interview at Apple II Reunion", interview by Jason
Scott, Internet Archive (`2015_06_Margot_Comstock_Interview`), **CC-BY 4.0**. Edited into a
vertical reel; motion graphics are original (hand-coded SVG/CSS/three.js generators); SFX from
the member's own library (picks in `data/sfx-map.json`; the library is not in the repo).

Output: `renders/FINAL.mp4` (1080×1920/30, −14.2 LUFS, −1.3 dBTP) · `renders/FINAL-sheet.jpg`.

## Wall time (4 vCPU, no GPU) — fresh run, nothing cached

| step | s | at |
| --- | --- | --- |
| 1a transcribe (faster-whisper small.en) | 25.3 | 25.3 |
| 2 plan — one Claude call ($0.11), overlapping vision | 44.8 | 70.0 |
| 1b vision (1080p decode: shots + faces) — finished | 14.8 | (inside 70.0) |
| 3 cut (EDL, remap) | 0.0 | 70.1 |
| 4 build: base video ∥ speech+SFX+mix ∥ HTML+DOM fit (12 scenes rescaled) | 31.6 | 101.7 |
| 5 render: 4 cost-weighted chunks in parallel (1756 frames) | 97.0 | 198.7 |
| 6 QC (flagged true peak −0.5) | 9.7 | 208.3 |
| audio auto-fix (re-mix with lower limiter ceiling + re-mux) | 8.7 | **≈ 217** |

The QC auto-fix is now built into `run.py` (it was added after this run, so it ran as a
separate 8.7 s step here).

## Not the same as v3 (memory/history.json fingerprints)

| | v3 (split-motion-dai) | #2 (this reel) |
| --- | --- | --- |
| scene types | chat, compare, custom_svg, doc, grid, hero3d, icon, orbit, quote, steps | bars, browser, counter, custom_svg, icon, list, phone, quote, radar, tree |
| shared types | — | 3 of 10 (custom_svg, icon, quote — and the SVGs/icons themselves differ) |
| identical type+enter+exit combos | 19 | 16 — **0 shared** |
| 3D | phone (hero3d) | none (no strong object in this script) |

Rebuild: `python3 -I kit/split-motion/harness/run.py SRC.mp4 split-motion-margot --sfx-lib LIB --plan split-motion-margot/data/plan.json --seed 58`
