---
name: split-motion
description: Turn ANY talking-head / podcast clip into a "split-motion" vertical reel (round-3 engine: Claude director + per-section Claude scene coders; no glow/slab/dust, content-lit depth, always-dynamic hero structures, flush geometry, density + frame gates). Originally: in the Kallaway style — top motion panel (dark or grid-paper, one evolving hero object per 1.5-3.5 s beat, headers with a serif-italic accent and a red box), wide speaker card at the bottom, 1-3 word seam captions, full-screen speaker punches every ~10 s, light cinematic risers + soft tick runs + rare flashes from the member's OWN SFX library, an optional licensed music bed, 1-3 three.js 3D hero moments. Driven by a fast harness (harness/run.py): raw clip in, finished reel out in ~5-8 min including render. HyperFrames 0.6.49 (HTML+CSS+GSAP), not Remotion.
---

# split-motion — MANDATORY RULES (owner, round 3; they override everything below)

Engine: `python3 -I kit/split-motion/harness/r3/run_r3.py RAW REEL --sfx-lib LIB --coder opus` — a Claude DIRECTOR
(Opus 5.5 high, one call) writes a storyboard; Claude SCENE CODERS (one call per section, in parallel) write bespoke GSAP
on the `harness/r3/lib.js` helpers; a validator + lint + repair loop and frame gates fail anything that breaks a rule.
Never hand the planner a fixed menu of scene types (round 2 failed exactly because of that).

1. **No glow, no slab, no dust — ever.** No radial gradients, blurred blobs, soft light glows behind objects, grey glowing
   panels behind diagrams, floating particles/orbs/dots, vignettes. The panel background is the flat deep colour
   (`#0a0a0c`) with at most the hairline grid. All light and depth come from the CONTENT: strokes, solid/linear fills,
   card rim + sheen from the section's key-light direction, shadows with real offsets. Blur only as a transient tween state.
   Gate: `r3/gates.py bg_gate` on 5 frames (particle count <= 4, smooth-blob area <= 1.2 %) + DOM style gate in
   `r3/validate.js` (radial-gradient / blur > 3 px / 0-offset glow shadows) + code lint. Any hit fails the render.
2. **Always dynamic, never drifting.** One persistent HERO STRUCTURE per 8–25 s section (script doc with highlighter rows,
   profile whose post grid fills, calendar/streak, tree/pipeline, phone feed, orbit of cards, chart, contract/offer,
   stacked pages, or a new one) that EVOLVES on the words; something meaningful changes every ~0.5–1 s; supporting
   elements arrive in staggered groups with soft overshoot; never "diagram, then wait"; no idle loops (yoyo/repeat),
   no tween > 1.2 s except one eased camera move per section; never the same structure in consecutive sections;
   sections transform into each other (push-through), never a blank panel.
3. **Flush geometry.** One source of truth: `harness/scenes.geometry()` (panel rect, card rect x 24 / w 1032 / y, radius 38,
   background colour, seam). Card band overlaid from the base video is range-converted (full → limited) so its black equals
   the panel black. Gate: `r3/gates.py geom_gate` samples the seam rows, both margins and both top corners on 5 frames —
   any deviation > 3 levels from the panel background, or a card edge not starting at its declared pixel, fails.
4. **Density gates** (`r3/density.py`): panel events 40–60/min, >= 3 visible elements >= 95 % of panel time, lonely-object
   time <= 5 %, ambient drift <= 20 %, jump detector 0 flagged (`harness/jumps.py`).
7. **Jigsaw (HARNESS.md › JIGSAW RULES):** approve cheapest first (text plan sheet → 540p still per section → full render);
   per-section render cache + splice, word-id anchors, heavy steps only via a `run_box.sh` bundle on the GPU box, wall time per step.
5. **Text:** never echo the captions; one header per section (bold sans + one *serif-italic* accent, optional [red box]
   word); numbers and real-looking UI text only.
6. **Kept:** tall speaker card (940 px of 1920), no device overflow (content clipped to phone screens), seam caption,
   Instagram danger zones, the member's own SFX only (12–18 dB under the voice, anti-repeat, risers on hero evolutions),
   −14 LUFS / ≤ −1 dBTP. Measure every step (`build/timings.json`, tokens in `build/tokens.json`).

---

# split-motion — Kallaway-style reels from any talking head

**Fast path (default): run the harness.** It does everything below in one command and
records wall time per step. Read [`HARNESS.md`](HARNESS.md) for the design.

```bash
python3 -I kit/split-motion/harness/run.py RAW.mp4 REEL_DIR --sfx-lib "SFX_LIBRARY_DIR" \
        --topic "what the reel is about" --len 55-72 --seed $RANDOM [--music LICENSED_BED.wav] [--theme light]
# -> REEL_DIR/renders/FINAL.mp4 (1080x1920, -14 LUFS, TP <= -1 dBTP) + FINAL-sheet.jpg + build/timings.json
```

Then **look** at `FINAL-sheet.jpg` next to a reference sheet and fix what is weak (§7): edit
`REEL_DIR/data/plan.json` and re-run with `--plan REEL_DIR/data/plan.json` (skips ingest
and the model; ~4 min). You are the editor, not a template filler.

| file | what |
| --- | --- |
| `harness/run.py` | the pipeline: ingest ∥ plan → cut → build (video ∥ audio+SFX ∥ HTML+fit) → chunked render → QC → memory |
| `harness/vocab.json` | the **motion vocabulary**: 20 scene types, 13 enter verbs, 10 exit verbs, 8 camera moves, header/caption styles, icons, 3D presets |
| `harness/scenes.py` | scene compiler: plan → HyperFrames HTML (one generator per scene type, seeded per reel) |
| `harness/runtime/kw.css`, `kw.js` | the Kallaway look (geometry, type, cards) and the motion verbs (`window.KW`) |
| `harness/novelty.py` + `memory/history.json` | anti-repeat for MOTION across reels |
| `harness/prompts/grammar.md` | the measured Kallaway grammar given to the planning model |
| `sfx/palette.json` | SFX **palette**: categories → several files of the member's library (names only) |
| `sfx/engine.py` | cues → SFX events with **anti-repeat + density enforced in code** |
| `sfx_mix.py` | the mixer: gains under the voice, peak alignment, optional ducked music bed, −14 LUFS / ≤ −1 dBTP |
| `research/` | the measurements behind every number here ([kallaway-20.md](research/kallaway-20.md), [music.md](research/music.md)) |
| `split-motion.css`, `sm-anim.js`, `components.html` | the v1 hand-built kit (still valid for fully manual reels; see `split-motion-dai/src`) |

## 1. Inputs (ask once, in one batch — only what you cannot infer)

1. the raw clip (any aspect; 16:9 multicam podcast or 9:16 selfie) + what the reel is about
2. target length (default 55–72 s of speech) — the model picks the story from the transcript
3. **the member's SFX library** (folder). No library → the reel ships without SFX (say so).
   Never synthesize sounds, never use sounds from anywhere else.
4. a **licensed** music bed if they want one (we never download songs; see research/music.md)
5. theme dark (default) or light grid paper; language (fonts must have its glyphs — Product
   Sans has Turkish; Instrument Serif Italic for accents)
6. credit line / license of the footage (goes in the reel README + meta.json)

## 2. Grammar (measured on Kallaway's 20 latest reels — research/kallaway-20.md)

**House rules from the owner (round 2) override the reference where they differ:** stillness is the
default — soft eased settles with a tiny overshoot, then hold; continuous camera (push / pull /
parallax / tilt) only on 2–4 hero beats; nothing slides across the frame. Scenes never echo the caption
words: the visual carries meaning (lit objects, drawings, 3D, numbers, light, particles, one shine);
text only for a header, a number or one key word. The speaker card is tall (`--speaker-h`, default
940 px of 1920).

| element | spec |
| --- | --- |
| layout | split **~71 %**: motion panel y 0–958 (near-black #0a0a0c + faint 90 px grid, or light grid paper), tall speaker card y 960–1900 (inset 24, r 38; `--speaker-h` sets the ratio — Kallaway's own is ~528) |
| speaker punches | full-screen 9:16 speaker **~29 %**, runs 1.5–4 s (median 3), one every 7–14 s, on opinion/punch lines; caption below the chin |
| graphic | full-screen graphic ≤ 1 beat per reel (rare in the reference) |
| header | y 150–330, ≤ 2 lines, bold sans + ONE *serif-italic* word, a phrase in a **red box** or a red underline; types on word by word; lives for its section |
| seam caption | 1–3 words, white bold ~58 px, just above the card (y 854 at the default geometry), x 90–990; quoted/key words in serif italic |
| hero | one per beat (1.5–3.5 s), literal to the words; sub-events on the spoken word (`at`); grows to fill the stage (QC fit) |
| cadence | one hero per 1.5–3.5 s beat, sub-events on the spoken word, holds in between; ambient-motion share of hold frames ≤ 25 % (QC); no dead panel > 5 s |
| hook | first sentence ≤ 4 s, header types with it; SFX densest here |
| CTA | "Comment 'WORD' to get …" 5–8 s before the end (only if the speaker says it) — stacked pages |
| music | a bed in every reel, **−17 dB under the voice**, ducked by speech |

## 3. SFX — the member's own library, palette + engine

**Palette** (`sfx/palette.json`, built by `sfx/build_palette.py` from
`research/tools/sfx_library.py` measurements of every file: type, length, attack, peak,
centroid, >4 kHz share, flatness). Several files per category, so nothing has to repeat:

| category | role | level (dB under voice) |
| --- | --- | --- |
| `riser_cine` (6) | light cinematic swell, **peak on** a chapter / reveal / punch / the intro | 12 |
| `riser_short` | 0.7–1 s swell into a scene swap | 12 |
| `riser_air` (3) | bright digital riser, low-passed — max 1 per reel | 16 |
| `whoosh_deep` (8) | panel → full speaker, chapter fly-through | 14 |
| `whoosh_soft` (8) | scene swap / slide / back to the panel | 15 |
| `tick_soft` (8) | **pıt pıt pıt**: counters, list rows, chips — the only category allowed in runs | 18 |
| `flash` (3) | white flash frame — max 2 per reel | 14 |
| `glow` (8), `ding` (5) | hero landing / check mark — never two in a row | 13 / 16 |
| `draw` (5) | lines, underlines, highlighter bars | 20 |
| `low_swell` | sub swell under the hook / CTA | 16 |

Kallaway's measured levels are ~4 dB hotter (risers/glows −8, pops −14); ours are softened
on purpose ("efendi gibi, çok kısık da değil").

**Engine rules (enforced in code, `sfx/engine.py`, re-checked in QC):**
1. never the same file twice in a row; rotate through a category before reusing a file
   (seeded order; the files the previous reel opened with go last — memory);
2. a category never on two consecutive events, except inside a tick run (files alternate);
3. density **16/min** (Kallaway 18), lowest-priority cues dropped first, min gap 0.35 s
   (0.12 s inside a tick run);
4. caps per reel: flash ≤ 2, riser_air ≤ 1, glow ≤ 4, ding ≤ 3;
5. risers/whooshes/glows are **peak-aligned** on their moment; voice stays raw.

The scene compiler emits the cues (layout switch → `punch`/`back`, chapter → riser, list rows
and counters → tick runs, hero landing → glow, line draws → draw, reel open → `intro` riser +
deep whoosh). The planner may add a rare `flash` / `reveal` / `ding` hint.

## 4. Motion vocabulary and anti-repeat (novelty)

* **Vocabulary** (`harness/vocab.json`, all compiled by `scenes.py`): scene types `orbit,
  doc, list, phone, grid, tree, radar, network, counter, compare, quote, bars, browser,
  chapter, cta, steps, icon, chat, hero3d, custom_svg`; enter verbs (soft settles) `settle, pop,
  focus, bloom, iris, wipe, unfold, tilt3d, flipY, zoomIn, fall, rise`; quiet exits `fade, dissolve,
  recede, lift, collapse, irisOut`; cameras `none` (default) and, on hero beats only, `push, pull,
  parallax, tilt`; header styles `box, underline, serif, plain`. Every scene also gets light,
  a decelerating particle burst and (every 3rd scene + heroes) one light sweep.
* **New designs every reel**: the model writes a fresh beat plan for *this* script and at
  least one **`custom_svg`** scene (a new line-art drawing for a concept the library lacks);
  every generator is **seeded per reel+beat** (layouts, radii, colours, stagger patterns,
  number styles vary).
* **Memory** (`memory/history.json`): each finished reel's fingerprint (types, verbs, cameras,
  header styles, type+enter+exit combos, first SFX files). The planner sees the last 3 reels
  and is told not to repeat them; `novelty.py` then enforces it: combos used by the last 3
  reels are re-rolled to the least-used verbs, consecutive beats never share an enter/exit/
  camera, > 60 % type overlap with the previous reel swaps decorative types.
* Consistency stays: same geometry, type, palette, card style and caption rules — chic and
  recognisable, never the same choreography.

## 5. 3D mode (1–3 hero beats per reel)

`scene.type = "hero3d"` with `preset` phone | coins | ring | cube | bars: three.js r181
(self-hosted `assets/vendor/three/`), glass/metal materials, RoomEnvironment reflections,
red key light, gentle UnrealBloom, deterministic (`window.__kw3d(t)` driven by the GSAP
timeline; renders only inside its beats). Use it only on the strongest concrete object. Cost
on CPU (SwiftShader): ~3× a flat frame — the render scheduler weights chunks for it.

## 6. Danger zones (Instagram / TikTok UI, 1080×1920)

| zone | rule |
| --- | --- |
| top `y 0–140` | nothing; headers start at y 150 |
| bottom `y ≈1560–1920` | the speaker card (face) only |
| right rail `x 960–1080, y 1050–1700` | no caption/chip/label (caption box x 90–990) |
| stage | split heroes live in x 40–1040, y 335–1205 — the DOM QC measures every beat and scales scenes in or out to fit |

## 7. Review (at least one look-and-fix round)

* `FINAL-sheet.jpg` (2 fps) next to a Kallaway sheet; `build/timings.json` has the QC block:
  loudness, true peak, jump/stutter frames (`build/jumps.json`, must be 0), ambient-motion share
  (≤ 25 %), card repeats, near-empty seconds; DOM QC fails content leaving a phone/browser.
* Weak spots to fix in `data/plan.json`: a hero that is not literal to the words, a beat
  > 3.5 s without a sub-event, a punch-in on a soft line, two similar scenes in a row, a
  header that stays too long, a missing CTA scene.
* Rules: deterministic only (no `Math.random`/`Date.now`/network in the page); every timed
  element is a `.clip` with data-start/duration/track-index; fromTo uses
  `immediateRender:false`; no template literals inside `querySelector`; free assets only.
* Credit the footage license in the reel README + meta.json. Never commit the SFX library,
  music, or presigned URLs.
