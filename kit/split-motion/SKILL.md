---
name: split-motion
description: Turn ANY talking-head / podcast clip into a "split-motion" vertical reel — a top motion panel (near-black dot grid, glowing hero objects that change every 1.5–3 s, a recurring chapter device the camera flies into) over a bottom speaker card, one-word seam captions on every spoken word, 4–5 full-screen punch-ins, soft SFX from the member's own library. Optional 3D mode (three.js glass/neon heroes with bloom). HyperFrames 0.6.49 (HTML+CSS+GSAP), not Remotion.
---

# split-motion — apply this style to any talking-head clip

You are the **editor**, not a template filler. You write the motion for *this* script,
render it, look at your own frames next to a reference, fix, and re-render. Do at least
two look-and-fix rounds. Nothing in this folder is tied to one person: every person-,
clip- or brand-specific value comes from the intake (§1) and lives in the reel folder.

| file | what |
| --- | --- |
| `split-motion.css` | theme: panel (dot grid, spotlight, card cut-out), header (bold sans + serif-italic accent, red underline), seam caption, hero frame, glow tokens, chips, coin list, chapter number, b-roll card, flash |
| `sm-anim.js` | `window.SMKit` GSAP helpers: `hero`, `pop`, `draw`, `typeHeader`/`headerOut`, `chapter`, `counter`, `word`, `punch`, `whipOut` |
| `components.html` | copy-paste markup: device ring, chapter numbers, coin list, connector line, chip, phone, chart, doc, b-roll card, recap |
| `sfx_mix.py` | SFX pre-mix from the **member's own library**: measures each pick, sets its gain under the voice, aligns envelope peaks to beats, fades, low-passes, mixes, −14 LUFS / ≤ −1 dBTP |

Worked example: `split-motion-dai/` (`src/template.html`, `scripts/`, `data/sfx-map.json`,
`demo-3d/`). Copy its `scripts/`. Only the KEEP / HOLD / CAMS / CROP / PUNCH tables at the
top of `edit.py`, and `data/sfx-map.json`, are rewritten per clip.

---

## 1. Inputs (ask once, in one batch)

1. the raw clip (any aspect; a 16:9 multicam podcast is fine) + what the reel is about
2. story beats / target length (default 55–75 s), or let you pick from the transcript
3. a reference reel to match, if any (you will contact-sheet it)
4. logos/watermarks to crop out; which person is the main speaker
5. palette and fonts (default black/white + neon red / neon green / gold; Product Sans +
   Instrument Serif Italic, self-hosted; check the fonts have the language's glyphs)
6. **the member's SFX library** (folder or zip). No library → ship the reel without SFX
   and say so. Never synthesize sounds; never use sounds from anywhere else.
7. credit line / license of the source footage (goes in the reel README + meta.json)
8. 3D mode wanted? (§8) — default off

## 2. Grammar (measured from a 92 s reference, 1080×1920)

| element | spec |
| --- | --- |
| layout | top **motion panel** y 0–1150 on near-black (#070708), faint plus/dot grid + soft spotlight; bottom **speaker card** y 1150–1920, inset 28 px, top corners r 44 |
| seam caption | ONE word at a time, white bold sans ~60 px, centred just above the seam (y 1046–1130), x 120–960, **every spoken word**; a few key words tinted gold/red/green |
| header | y 168–310, bold sans + **serif-italic accent** with red underline; types on word by word; lives for its section |
| hero object | one per beat, panel centre (y≈680), glowing; **fills 60–70 % of the panel width** (≈650–750 px); enters scale-up + blur-in ~0.3 s, drifts while alive, exits scale/blur ~0.25 s; lives 1.5–6 s with sub-events (counter ticks, chips, lines drawing) |
| cadence | the panel changes every **1.5–3 s**; never a static or near-empty panel (no dark-on-dark scenes: tiles/outlines need ≥ 40 % white) |
| connector lines | SVG paths `pathLength="1"` drawn between related objects (`SMKit.draw`) |
| chapter device | one recurring glowing object (ring, loop, ...). The camera flies INTO it (~1.3 s) while a big number + label punch in. 3–4 chapters per reel |
| lists | gold numbered coin + short text line, one row per spoken item |
| b-roll card | rounded card with another clip/still + green label chip, swaps on the beat |
| punch-ins | 4–5 × full-screen 9:16 speaker for 1–3 s on emphasis lines (crop from the 4K source), panel hidden, video 1.12→1 + light flash |
| recap ending | the chapter device with every chapter label around it + a closing header |
| palette | black/white, neon red #ff3346, neon green #39ff8f, gold #ffc53d |

## 3. Steps

1. **Contact-sheet the reference** at 1–2 fps (`fps=1,scale=216:384,tile=10x10`) and a few
   full-res frames. Confirm the table above (seam y, caption size, header y, hero size).
2. **Transcribe** with whisper.cpp (build it: `cmake -B build && cmake --build build -j$(nproc) --target whisper-cli`):
   `whisper-cli -m ggml-small.en.bin -f a16k.wav -ojf -ml 1 -sow` (+ `--dtw small.en -nfa` for
   token times — `-nfa` is required). Word offsets drift ±0.4 s: **never cut on them**.
3. **Story cut** (`edit.py`): KEEP ranges by beats; every boundary inside a measured energy
   dip (≥ 30 ms below −42 dBFS, 10 ms RMS scan). Internal silences tighten to ~0.2 s
   (0.3–0.45 s before a payoff). **Verify**: re-transcribe the cut audio and diff the text.
4. **Cameras + crops**: scene-detect the multicam (`select='gt(scene,0.2)'`); per camera a
   1080:770 crop (face upper-middle, logo outside), a tighter `_z` crop for jump cuts on
   the same camera, a 9:16 punch crop on the main speaker. `edit.py` writes `base.mp4`
   1080×2040 full-range `yuvj420p` (padded to 2040, see CLAUDE.md), then
   `ffmpeg -i base.mp4 -c:v copy -an assets/video.mp4` (VIDEO-ONLY).
5. **Captions** (`captions.py`): words from the CUT audio, onset = DTW − 0.1 s snapped to the
   nearest energy onset; ≥ 3 frames apart. `build.py` shows each word **2 frames early**
   (the pop takes 0.1 s, a caption exactly on the onset reads late).
6. **Beat sheet** before any markup: for every 1.5–3 s window — hero object, sub-event,
   header, chapter, SFX (if any). Map objects to the *literal* words.
   Chapter fly-ins on breath points, punch-ins on the 4–5 strongest lines.
7. **Assemble** `src/template.html` → `build.py` → `index.html`. Tracks: 0 video · 2 panel
   (all motion inside one panel clip, heroes animated by GSAP) · 3 captions · 4 flash ·
   8 audio (ONE mixed file).
8. **SFX** (§5) → `assets/mix.wav`.
9. `npm run check` → **0 errors**. `hyperframes snapshot --at t1,t2,... --describe false`
   on a dozen changed beats first (~15 s vs ~10 min for a render).
10. **Render** `npm run render -- -w $(nproc)` (1080×2040) →
    `ffmpeg -i raw.mp4 -vf crop=1080:1920:0:0 -c:v libx264 -crf 18 -c:a copy FINAL.mp4`.

## 4. Danger zones (Instagram / TikTok UI, 1080×1920) — light touch

| zone | rule |
| --- | --- |
| top `y 0–140` | nothing; headers start at y 168 |
| bottom `y ≈1560–1920` | speaker card (the face) only: no caption, chip or label |
| right rail `x 960–1080, y 1050–1700` | no caption/chip/label; seam caption box is x 120–960 |
| centred text | ≤ 840 px wide; hero chips that drift must stay inside x 40–1040 |

During punch-ins the seam caption must sit below the chin, never on eyes/mouth.

## 5. SFX — the member's own library, soft and sparse

1. **Measure the library** (all files, `-I` Python, ffmpeg): length, integrated LUFS, true
   peak, envelope (onset, peak time, attack), spectral centroid / energy above 4 kHz.
2. **Pick by role** — soft, smooth, glowy; reject harsh (fast attack + centroid > 6 kHz
   unless low-passed), cartoonish, electric/zap, alarm, cash-register, boom:

   | role | look for | where |
   | --- | --- | --- |
   | glow entrance | shine / shimmer / hologram-appear (slow attack, swell) | 3–6 hero entrances, not all |
   | chapter fly-in | soft **deep** whoosh (centroid < 600 Hz) | every chapter; alternate 2 files |
   | big reveal | gentle riser (peak aligned on the reveal) + a sparkle instead of a boom | once |
   | key reveal | very quiet UI tick / bloop / soft pop | 3–5 in the whole reel |
   | line draw | marker / pen draw | connector lines, signatures, stairs |
   | punch-in | darkest, softest whoosh | 1–2 punch-ins, not all |

3. **Shape every hit**: fade-in 5–20 ms, low-pass harsh ones (5–9 kHz), set each pick
   **14–20 dB under the voice** (max momentary loudness vs speech integrated; whooshes/riser
   14–16, glows 17–18, ticks/markers 20). Align by envelope peak (`"align": "peak"`).
4. **Write `data/sfx-map.json`** (file names relative to the library, `peak_ms`, fade,
   low-pass, `under_voice_db`, events with time + reason). Commit the map, **never the
   library or a download URL**.
5. `python3 -I kit/split-motion/sfx_mix.py gain MAP LIB speech.wav` then
   `... mix MAP LIB speech.wav assets/mix.wav TOTAL`. Voice stays raw: one linear gain to
   **−14 LUFS integrated**, limiter, **true peak ≤ −1 dBTP** (the tool verifies).
6. Budget: roughly one SFX per 3 s of reel at most; never on every caption or object.

## 6. Review rounds (minimum two)

Each round:

* 1–2 fps sheet of yours and of the reference side by side (same tile size);
* `python3 -I scripts/qc_motion.py FINAL.mp4` → static runs > 3 s must be **0**, longest gap
  between major panel changes ≤ 3 s;
* near-empty frames: the panel's lit-pixel coverage (y 300–1060, luma > 70) under ~1.5 %
  for more than 0.3 s outside a transition = fix (bigger/brighter object, earlier sub-event);
* list where yours is weaker: hero < 60 % of panel width, static seconds, caption over a
  face, object in a danger zone, header colliding with an object, punch-in on a soft shot,
  SFX too loud / harsh / too many;
* fix in the template, rebuild, re-render; write the list + fixes in the reel README.

## 7. Rules

* **Every spoken word gets a seam caption, one word at a time.** Nothing else on screen is
  more than ~5 words (headers 2–4 words).
* Never cover the speaker's face.
* `fromTo` tweens placed late paint their FROM state at t=0 — use `immediateRender:false`
  for anything that must stay visible before it (see `SMKit.punch`).
* Deterministic only (no `Math.random`, `Date.now`, network). Generate geometry in `build.py`.
* No template literals inside `querySelector` (the bundler rejects them).
* Free assets only: hand-drawn SVG/CSS with glow, CC footage. No paid generation / APIs.
* Credit the source license in the reel README and meta.json. Never commit presigned URLs.

## 8. 3D mode (optional, 1–3 hero beats per reel)

What it adds: real lit 3D for the hero objects — the chapter device as a **glossy glass
neon tube** (transparent clear-coated torus over an emissive core), objects such as a glass
phone with a live canvas-texture screen and metallic gold coins, environment reflections
(`RoomEnvironment` + PMREM), coloured point lights, slow rotation, a camera that flies
*through* the device, and **UnrealBloom** for the glow. Example: `split-motion-dai/demo-3d/`.

* three.js **r181**, self-hosted under `assets/vendor/three/` (build + the needed `addons/`),
  loaded with an import map + `<script type="module">`; no CDN at render time.
* `WebGLRenderer({ preserveDrawingBuffer: true })`, `setPixelRatio(1)`, ACES tone mapping,
  `EffectComposer` → `RenderPass` → `UnrealBloomPass` → `OutputPass`. Bright parts use
  `MeshBasicMaterial({ color: >1, toneMapped: false })` so only they bloom.
* **Deterministic**: the scene is a pure function of `t`; one GSAP tween drives it
  (`tl.to(P, { t: DUR, onUpdate: () => frame(P.t) })`), no clocks, no rAF loop.
* Keep HTML text (headers, captions) as DOM on top of the canvas.
* Cost: without a GPU HyperFrames falls back to SwiftShader (CPU). Measure s/frame on a
  snapshot first; use 3D for short beats, the flat SVG grammar for the rest.
