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

## Round 2 (2026-11-19) — owner feedback applied

Feedback (Nail): too much sliding/drifting "like Kallaway"; scenes repeated the caption words;
speaker area too narrow; content spilled out of the phone; small hitches/jumps in graphics.

| ask | what changed | where |
| --- | --- | --- |
| motion language | stillness is the default: soft eased settles (`back.out(1.15)` / `expo.out`, 0.5–0.8 s) then HOLD; continuous camera (push/pull/parallax/tilt) only on 2–4 **hero** beats (validator caps ~1 per 6 beats, non-hero camera forced to `none`); slide/whip/bounce verbs removed (old names alias to soft ones); no panel slide on layout return; no orbit rotation / number creep unless hero | `runtime/kw.js`, `vocab.json`, `scenes.py`, `planner.validate`, `prompts/grammar.md` |
| motion budget | QC measures the share of in-beat hold frames with ambient motion (drift) — gate ≤ 25 % | `jumps.py` → `5b jump QC`, `qc.final` |
| less literal | planner prompt forbids echoing caption words; text only for header / a number / one key word; validator flags scene text that repeats the beat's (±1) caption words and strips echoing labels (caption-echo quotes become glass objects); every scene gets **light + particles + one cinematic shine** (all settle into stillness); icons are now lit glass objects (glow, rim light, highlight, drawn icon) | `planner.py`, `scenes.fx_layers`, `gen_icon` |
| taller speaker | layout is a function of the card height: `--speaker-h` (default **940 px of 1920**, card y 960–1900, panel 0–958, seam caption at y 854); the 880-px design frame is scaled into the shorter stage and the DOM fit regrows heroes (cap 2.1×) | `scenes.geometry`, `cut.set_geometry`, `qc.set_geometry`, `render(band_y)` |
| phone overflow | phone/browser content lives in a `.screen` with `overflow:hidden` + inset; DOM QC fails any visible child whose box leaves its `[data-device]` and auto-shrinks that screen's content, then recompiles (loop) | `gen_phone`, `gen_browser`, `qc_dom.js`, `qc.dom_fit`, `run.py` |
| stutter / jumps | root causes found and fixed (below) + automatic detector with re-render loop | `jumps.py`, `run.py 5b` |

### Root causes of the hitches (found on the round-1 margot/dai renders)

1. **Final-state flash, then reset** — every sub-element tween used `immediateRender:false`, so
   until its start time an element showed its FINISHED state (full bars, revealed rows) and then
   snapped back to its start and animated (margot 28.6 s: bars full → collapse → regrow). Fix:
   `KW.scene(t0)` + `KW.ft()` apply each tween's FROM state at its scene start; the compiler routes
   every generator `fromTo` through it.
2. **Line draws popped instead of drawing** — GSAP's CSSPlugin auto-rounds px values; with
   `pathLength=1` the CSS `stroke-dashoffset` went 1px → 0px in ONE frame mid-tween (icons,
   connectors, custom SVGs). Fix: tween the SVG *attribute* (`attr:{'stroke-dashoffset'}`).
3. **Counter jitter** — proportional digits re-centred every frame while counting; 0→1 counters
   jumped in a single step. Fix: tabular figures; small integers settle instead of counting.
4. **Class snapping** — list-row highlights toggled `className` (one-frame change). Fix: eased
   `KW.light` / `KW.unghost` state tweens.
5. **Duplicated frames in the speaker card** — the 29.97 fps source (and the 30 fps mezzanine)
   went through the `fps` filter, which inserts a duplicate every ~33 s and at sub-segment starts
   (5 in the margot base video). Fix: frame renumbering 1:1 per sub-segment (`setpts=N/(30*TB)`)
   for ~30 fps inputs; only true 60 fps input is decimated. Remaining dai card repeats come from the
   source itself: its 4K60 file carries **24p footage with 2:3 pulldown**, so 24 unique frames/s
   on a 30 fps timeline must repeat some frames.
6. Not a cause (measured): chunk seams and the per-chunk GSAP time-wrap — seam frame-diff ratios
   1.15–1.34 vs neighbours, no repeated frames at any seam.

### Automatic jump detector (`harness/jumps.py`, QC step 5b)

Every frame of the motion panel (y 150 → seam caption, 270 px wide, 6×6 tiles):
`repeat` (identical frame inside running motion), `pop` (a tile changes and reverts next frame),
`snap` (a tile changes in one frame with calm frames around it, inside a hold), `seam` (chunk
boundary outlier); planned cuts and exit windows are excluded, entrance wipes/irises are judged
only for repeats/pops. Plus `card_repeats` in the speaker card and the ambient-motion share.
`run.py` re-renders only the chunks with render-side defects (repeat/seam/pop) and re-checks
(max 2 loops); composition defects (snaps) fail the QC report.

| render | flagged frames | ambient-motion share (holds) | card repeats |
| --- | --- | --- | --- |
| dai round 1 (`FINAL-v3.mp4`) | 4 (snap 4) | 0.58 | 3 |
| margot round 1 (`FINAL.mp4`) | 6 (snap 4, pop 1, repeat 1) | 0.54 | 0 (5 in its base video) |
| **dai round 2 (`FINAL-v4.mp4`, final)** | **0** | **0.12** | 2 (source 2:3 pulldown) |
| **margot round 2 (`FINAL-v2.mp4`, final)** | **0** | **0.155** | **0** |

The detector also caught two composition bugs in round 2's own first renders, both fixed: the
cinematic shine switched on/off with its band in view (one-frame panel flash) and then crossed
~5 panel widths in 1.3 s (~140 px/frame flicker) — it now travels 1.8 widths with an opacity
envelope, and it is a hero-only effect (with a shine every 3rd scene the ambient-motion share
was 33–35 %, over the 25 % budget). One residual flag remains in the gpt62sol trial render: a
doc card's 1-px placeholder lines alias for a frame during its settle (57.07 s).

(While building the detector, an earlier whole-panel version flagged 13 / 19 frames on the round-1
renders; the table uses the final detector for all four.)

### Round-2 wall times (fresh, nothing cached, one Claude planning call)

| step | dai v4 (4K60 VP9 multicam) | margot v2 (1080p H.264) |
| --- | --- | --- |
| 1a transcribe | 22.5 s | 20.7 s |
| 2 plan (overlaps vision) | 78.8 s ($0.16) | 37.3 s ($0.11) |
| 1b vision — done at | 101.3 s | 57.9 s |
| 4 build (video ∥ audio+SFX ∥ HTML + DOM fit) | 48.6 s | 41.5 s |
| 5 render (4 chunks) | 128.5 s | 155.9 s |
| 5b jump QC (+loop) | 9.7 s | 11.1 s |
| 6 QC | 11.9 s | 13.3 s |
| **total incl. render** | **300.0 s (5.0 min)** | **279.7 s (4.7 min)** |
| look-and-fix re-render (same plan, cached ingest, 4 chunks, alone) | 200.0 s | — |
| final re-render (shine fixes; 2 chunks, sharing the 4 cores with 2 other reels) | 551.0 s | 564.6 s |

The richer scenes (glow, particles, shine) cost render time: margot's render went 97 → 156 s.
Capacity lesson: five reels at once (10 Chrome workers, 15 GB RAM) got renderer processes
OOM-killed and all five failed; three at once (6 workers) is safe here. Chunk renders now
retry once before failing the reel.

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

### Planner trial (same dai transcript, same prompt, 2026-11-19)

| model | result | time | cost | scene types |
| --- | --- | --- | --- | --- |
| openai/gpt-6.2-sol (OpenRouter) | valid plan | 42 s | $0.04 | 8 |
| Claude Opus 5.5 (high) | valid plan | 122 s | — | 13 |
| google/gemini-4-carbon (OpenRouter) | invalid JSON with `response_format: json_object` + `max_tokens 16000`; a plain call with `max_tokens 32000` returned valid JSON | 34 s | $0.033 | 13 |

`models.json` now has an **`openrouter`** adapter (disabled by default): any model id; the key is
read in code from `~/.config/tigno/openrouter.key` at call time (never in git, env or logs); no
`response_format`, `max_tokens` 32000; invalid JSON → local repair (fences, trailing commas,
truncation) → one retry asking the same model to fix its JSON → else the `local` planner.
Renders of the three plans: see "Planner-trial renders" below.

### Planner-trial renders (2026-11-19) — `split-motion-dai/renders/planner-trial/`

Three plans for the same dai cut (`kit/split-motion/research/planner-trial-1119/*.plan.json` on
`claude/planner-plans-1119`; word indices = the round-1 cut words), each rendered with the round-2
harness: same raw, same cut (`--cut-from`, all words kept, no re-cut), seed 41, same SFX/mix rules,
`--no-novelty` (memory neither alters nor records them). The same round-2 validator ran on all three
(it strips caption-echo labels and turns caption-echo quotes into glass objects). Not judged here.

| plan | MP4 | wall time | conditions | QC |
| --- | --- | --- | --- | --- |
| gpt62sol | `gpt62sol.mp4` | 719.0 s | batch of 3 reels on 4 cores, 2 chunks; includes one 192 s chunk re-render by the QC loop | 1 flagged (doc settle aliasing), ambient 0.089 |
| gemini4carbon | `gemini4carbon.mp4` | 373.8 s | batch of 2 reels, 2 chunks | 0 flagged, ambient 0.086 |
| opus55 | `opus55.mp4` | 375.4 s | batch of 2 reels, 2 chunks | 0 flagged, ambient 0.142 |

Side-by-side sheet: `planner-trial-sheet.jpg` (3 columns, same timestamps every 3 s); per-reel
2 fps sheets next to each MP4. Projects (plans as validated, index.html, beats): `split-motion-dai/planner-trial/<name>/`.

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
