# split-motion HARNESS — raw talking head in, finished reel out in 5–8 min

Written for this repo's agents and for Tigno later: everything an orchestrator needs to run,
extend or port the pipeline. Code: [`harness/`](harness/). Style rules: [`SKILL.md`](SKILL.md).
Measurements behind the rules: [`research/kallaway-20.md`](research/kallaway-20.md).

```bash
python3 -I kit/split-motion/harness/run.py RAW.mp4 REEL_DIR --sfx-lib "SFX_LIBRARY_DIR" \
  [--topic "..."] [--len 55-72] [--seed N] [--theme dark|light] [--music BED.wav] \
  [--model claude|local|anthropic|openai|gemini] [--chunks N] [--out FINAL.mp4] [--plan plan.json]
```

Outputs: `FINAL.mp4` (1080×1920/30, −14 LUFS, TP ≤ −1 dBTP), `FINAL-sheet.jpg` (2 fps),
`REEL_DIR/data/{plan,edl,words,beats,sfx-map}.json`, `REEL_DIR/index.html` (preview in
`npm run dev`), `REEL_DIR/build/timings.json` (every step's wall time + the QC block).

## Pipeline

```
 t=0 ──┬─ transcribe  faster-whisper small.en int8 (word times, VAD) ──┐  ~18 s
       ├─ vision      ONE decode: 5 fps gray → shot cuts (histogram) + Haar faces per shot,
       │              1 fps sheet, and (4K/60 sources) a 1080p/30 H.264 mezzanine  ~45–60 s
       └─ energy      10 ms RMS envelope                                     <1 s
             │ transcript ready
             └─ PLAN  ONE model call (prompt = grammar + vocabulary + memory + indexed
                      transcript) → plan.json; validated + repaired in code; novelty pass
                      (runs WHILE vision is still decoding)                  ~70 s
 CUT    EDL from word ranges, boundaries snapped to 10 ms energy dips, pauses > 0.35 s
        tightened; words remapped; beat times; faceless speaker beats → split   <0.1 s
 BUILD ─┬─ base video: per sub-segment ffmpeg (input seek, exact frame counts) in parallel,
        │  card from the mezzanine, punch-ins from the original, lossless concat   ~35–45 s
        ├─ speech cut (numpy, 6 ms joint fades) → SFX engine (cues → events, rules in code)
        │  → sfx_mix (cached per-file loudness, peak alignment, −14 LUFS, ≤ −1 dBTP)   ~5 s
        └─ HTML compile → DOM QC (headless Chrome measures every scene) → fit → recompile ~40 s
 RENDER N = nproc frame-exact chunks, cost-weighted (3D ×3, video frames ×1.6), rendered
        concurrently; the page carries <video> only in full-screen speaker runs; each chunk is
        overlaid with the card band from the base video + cropped to 1920 as it finishes;
        lossless concat + AAC 320k mux                                        ~110–150 s
 QC     loudness + true peak, motion (static runs, changes/min, near-empty), SFX rule check,
        2 fps sheet                                                            ~10 s
 MEMORY the reel's motion/SFX fingerprint → memory/history.json (next reel avoids it)
```

## Measured wall times (4 vCPU Xeon 2.1 GHz, 15 GB, no GPU)

| step | proof v3 — 4K60 VP9 multicam, 86 s raw → 65 s reel | proof #2 — 1080p H.264 single cam, 120 s raw → 58 s reel |
| --- | --- | --- |
| 1a transcribe | 49.0 s (cold model load) | 25.3 s |
| 2 plan (Claude, overlaps 1b) | 64.6 s ($0.12) | 44.8 s ($0.11) |
| 1b vision (one decode) | 73.1 s — done at 113.6 | 14.8 s — done at 70.0 |
| 3 cut | 0.0 s | 0.0 s |
| 4 build (video ∥ audio+SFX ∥ HTML+fit) | 40.7 s | 31.6 s |
| 5 render (4 chunks) | 134.0 s (1958 frames, 3D beat) | 97.0 s (1756 frames) |
| 6 QC (+ audio auto-fix) | 10.6 s | 9.7 s + 8.7 s |
| **total, fresh, incl. render** | **298.9 s = 5.0 min** | **≈ 217 s = 3.6 min** |
| re-run from the same plan (cached ingest, no model) | 174 s | — |

Earlier dev numbers for reference: render before the speaker-only-video change 140–190 s;
base video before the mezzanine 58 s; ingest before overlapping the planner ~63 s + plan 70 s.

## Why it is fast (and where the time goes)

| decision | effect |
| --- | --- |
| planner starts when the transcript is ready, overlapping the vision decode | hides ~60 s |
| one decode of the source for shots + faces + sheet + mezzanine | a 4K60 VP9 decode is ~1.75× realtime on 4 cores — never do it twice |
| card cut from a 1080p mezzanine, only punch-ins read the 4K original | base video 58 s → ~35 s |
| `<video>` only during full-screen speaker runs; card band composited by ffmpeg | `<video>` costs ~40 ms/frame in the renderer: split frames render ~1.8× faster |
| N concurrent chunk renders, cost-weighted, crop overlapped | all cores busy through capture, encode and crop; the 3D chunk no longer straggles |
| SFX loudness cached in `sfx/palette.json` (`max_m`) | one voice measurement instead of one per sound |
| ingest cache keyed by file+size+mtime+model | re-runs (`--plan` edits) start at the cut: ~3–4 min |
| AAC at 320k | 192k overshot the limiter by 1.7 dB (TP +0.2); 320k keeps −1.5 dBTP |

What did NOT help (measured, 300-frame chunk): 1 render × 4 workers vs 4 × 1 vs 2 × 2 —
all 25.6–26.9 s (CPU-bound screenshot capture); `chrome-headless-shell` (beginFrame path)
was *slower* here (41 s, software compositing); alpha output (MOV ProRes 4444 / WebM VP9
alpha) 62–65 s — encoding alpha costs more than the video element it removes.

## Model slot

`harness/models.json`. Only the PLAN step calls a model; everything else is code.

| step | model tier | why |
| --- | --- | --- |
| plan (story cut, beats, scene specs, custom SVG) | **strongest** (Claude by default via `claude -p`) | taste, literal word→object mapping, novelty vs memory, drawing new SVGs |
| plan repair | none (code) / cheap fallback | `planner.validate` fixes indices, unknown types/verbs, duplicates |
| transcribe / vision / QC | local | faster-whisper, OpenCV, ffmpeg, headless Chrome |
| (later) visual QC critique | cheap VLM | optional: describe the sheet, flag weak beats |

Adapters: `claude` (CLI, default), `anthropic` (Messages API), `openai` (Chat Completions,
JSON mode), `gemini` (generateContent, JSON mime) — the three API adapters are written but
**disabled** (`"enabled": false`) so nothing paid runs by accident; flip one on to trial it
(`--model openai`). `local` = keyword heuristics + seeded variety, no model, ~0.1 s (dry runs,
timing, offline). A bad/invalid model answer falls back to `local` and is logged.

Cost: one plan ≈ 9.5 k prompt chars → $0.15–0.27 per reel with the CLI default model,
66–74 s API time. A faster model id in `models.json` trades some taste for ~2× speed.

## Caches

* whisper models (`~/.cache/huggingface`), demucs model (research only), HyperFrames
  fonts (`~/.cache/hyperframes/fonts`), npx package (warmed in the background at t=0)
* per reel: `build/ingest.key` + words/shots/energy/proxy (re-runs skip ingest)
* `sfx/palette.json`: picks + per-file loudness; `memory/history.json`: novelty
* fonts / gsap / three.js are staged once into the reel folder (`stage_project`)

## Contracts (for porting to Tigno)

* **plan.json** — `{title, theme, accent2, keep:[[w0,w1]...], emph:[w...], beats:[{w0, layout:
  split|speaker|graphic, header:{text,style}, scene:{type, enter, exit, camera, ...fields, at:[w...]},
  sfx:[...]}]}`; word indices refer to `build/words.json` (original timeline). Schema + fields
  per type: `harness/vocab.json`.
* **cues → events** — `sfx/engine.py plan(palette, cues, seed, per_min, total, memory)`;
  cues `{t, role, prio?, run?}`; events `{t, sound "cat:file", cat, role, align}`.
* **chunk HTML** — `scenes.compile_reel(plan, words_cut, total, ctx, chunk=(off, dur))`: the
  master GSAP timeline is wrapped (`W.fromTo(tl,{time:off},{time:off+dur})`), clips are
  shifted, `<video data-media-start>` keeps media time.
* Everything is deterministic: same plan + seed → same frames.

## Known gaps / next steps

* The 4K60 VP9 source decode (~50 s) is the floor of ingest; typical phone footage
  (1080p H.264) decodes ~10× faster (proof 2).
* Render is CPU-bound screenshot capture (~11.5 fps for video frames, ~21 fps for overlay-
  only frames on 4 cores). A GPU box, or more cores, scales it linearly (chunks = nproc).
* The planner call is ~70 s; a faster model or streaming the JSON straight into the compiler
  would cut it.
* SFX taste is rule-based (palette + engine); there is no ear in the loop — listen once per reel.
