---
name: split-motion
description: Turn ANY talking-head / podcast clip into a "split-motion" vertical reel — a top motion panel (near-black dot grid, glowing hero objects that change every 1.5–3 s, a recurring chapter device the camera flies into) over a bottom speaker card, one-word seam captions on every spoken word, 4–5 full-screen punch-ins. HyperFrames 0.6.49 (HTML+CSS+GSAP), not Remotion.
---

# split-motion — apply this style to any talking-head clip

You are the **editor**, not a template filler. You write the motion for *this* script,
render it, look at your own frames next to a reference, fix, re-render. Minimum two
look-and-fix rounds.

Files in this folder:

| file | what |
| --- | --- |
| `split-motion.css` | theme: panel (dot grid, spotlight, card cut-out), header with serif-italic accent + red underline, seam caption, hero frame, glow tokens, chips, coin list, chapter number, b-roll card, flash |
| `sm-anim.js` | `window.SMKit` GSAP helpers: `hero` (scale+blur in, drift, out), `pop`, `draw` (connector lines), `typeHeader`, `chapter` (fly-in), `counter`, `word`, `punch` |
| `components.html` | copy-paste markup: device ring, chapter numbers, coin list, connector line, chip, phone, chart, doc, b-roll card, recap |
| `sfx/make_sfx.py` | deterministic license-free whoosh / riser / boom / pop / tick (fallback when the user has no SFX library) |

A complete worked example lives in `split-motion-dai/` (`src/template.html` + `scripts/`).
Copy its `scripts/` (edit, captions, build, mix, qc_motion) — none of them hold
person-specific constants except the KEEP / CAMS / CROP / PUNCH tables at the top of
`edit.py`, which you rewrite per clip.

---

## 1. Inputs (ask once, in one batch)

1. the raw clip (any aspect; 16:9 multicam podcast is fine) + what the reel is about
2. the story beats / target length (default 55–75 s) — or let you pick from the transcript
3. a reference reel to match, if any (you will contact-sheet it)
4. logos/watermarks that must be cropped out; who the main speaker is
5. palette override (default black/white + neon red, neon green, gold) and fonts
   (default Product Sans + Instrument Serif Italic, self-hosted)
6. their SFX library path (else generate with `sfx/make_sfx.py`)
7. credit line / license of the source (put it in the reel README + meta.json)

## 2. Grammar (measured from the reference, 92 s, 1080×1920)

| element | spec |
| --- | --- |
| layout | top **motion panel** y 0–1150 on near-black (#070708) with faint plus/dot grid + soft spotlight; bottom **speaker card** y 1150–1920, inset 28 px, top corners r 44 |
| seam caption | ONE word at a time, white bold sans ~60 px, centred just above the seam (y≈1046–1130), **every spoken word**; a few key words tinted gold/red/green |
| header | top y≈168–310, bold sans + **serif italic accent** word with red underline; types on word by word; persists for its section; swaps with the section |
| hero object | one per beat, panel centre (y≈680), glowing; enters scale-up + blur-in ~0.3 s, slow drift while alive, exits scale/blur ~0.25 s; lives 1.5–6 s, with sub-events (counter ticks, chips, lines drawing) so nothing is static |
| cadence | the panel changes every **1.5–3 s**; never a static panel |
| connector lines | SVG paths `pathLength="1"` drawn between related objects (`SMKit.draw`) |
| chapter device | a recurring glowing object (reference: red infinity loop; example: red PREP RING). Camera flies INTO it (scales past the frame, ~1.3 s) while a big number + label punch in («1 the shout-out»). 3–4 chapters per reel |
| lists | gold numbered coin + short text line, one row per spoken item |
| b-roll card | rounded card holding another clip/still + green label chip, swaps on the beat |
| punch-ins | 4–5 × full-screen 9:16 speaker for 1–3 s on emphasis lines (crop from the 4K source = sharp); panel hidden, video scale 1.12→1 + white flash |
| recap ending | the chapter device with every chapter label around it + a closing header |
| palette | black/white, neon red #ff3346, neon green #39ff8f, gold #ffc53d |

## 3. Steps

1. **Contact-sheet the reference** at 2 fps (`ffmpeg -vf "fps=2,scale=180:320,tile=12x8"`) and
   a few full-res frames. Confirm the table above (seam y, caption size, header y).
2. **Transcribe** the raw clip with whisper.cpp: `whisper-cli -m ggml-small.en.bin -f a16k.wav -ojf -ml 1 -sow`
   (+ `--dtw small.en -nfa` for token times — `-nfa` is required, DTW is disabled with flash attention).
   Whisper word offsets drift by up to ±0.4 s: **never cut on them**.
3. **Story cut** (`edit.py`): choose KEEP ranges by beats; put every boundary inside a
   measured energy dip (≥30 ms below −42 dBFS — list them with a 10 ms RMS scan). Internal
   silences are tightened to ~0.2 s automatically (keep 0.3–0.45 s before a payoff).
   **Verify**: re-transcribe the cut audio and diff against the expected text — any clipped
   or missing word means move that boundary.
4. **Cameras + crops**: scene-detect the multicam (`select='gt(scene,0.2)'`), give each camera a
   1080:770 crop (face upper-middle, logo outside), a tighter `_z` crop to hide jump cuts on
   the same camera, and a 9:16 punch crop on the main speaker camera. `edit.py` writes
   `base.mp4` 1080×2040 (speaker in y 1150–1920, top black; punch-ins full 9:16) — full-range
   `yuvj420p`, padded to 2040 (renderer bottom-drop safety, see CLAUDE.md).
5. **Captions** (`captions.py`): words from the CUT audio, onset = DTW − 0.1 s snapped to the
   nearest energy onset; ≥3 frames apart; no clip overlap on track 3.
6. **Beat sheet** — write it before any markup: for every 1.5–3 s window, which hero object,
   which sub-event, which header, which chapter. Map hero objects to the *literal* words
   (counter racing on "followers", DM bubble on "shout me out", fireworks on "fireworks").
   Put chapter fly-ins on natural breath points, punch-ins on the 4–5 strongest lines.
7. **Assemble** `src/template.html` → `build.py` → `index.html`. Track convention: 0 video ·
   2 panel (everything motion lives inside one panel clip; heroes are children animated by
   GSAP) · 3 captions · 4 flash · 8 audio. Speaker video is VIDEO-ONLY; audio is one mixed file.
8. **SFX pre-mix** (`mix.py`): whoosh on chapter fly-ins (and soft on punch-ins), soft pops on
   hero entrances, ticks on list rows, ONE riser landing on the payoff + boom. Two-pass
   `loudnorm` to **−14 LUFS / −1.5 dBTP**.
9. `npm run check` → **0 errors**. Snapshot (`hyperframes snapshot --at ...`) a dozen beats
   before the first full render — it is ~25 s instead of ~10 min.
10. **Render** `npm run render` (1080×2040) → `ffmpeg -vf crop=1080:1920:0:0 -c:a copy FINAL.mp4`.

## 4. Review rounds (minimum two)

Each round:

* 2 fps sheet of yours and of the reference side by side (same tile size);
* `python3 -I scripts/qc_motion.py FINAL.mp4` → static runs > 3 s must be **0**, and the
  longest gap between major panel changes should be ≤ 3 s (the reference measures 0.6 s per
  major change on average, longest gap 5.4 s);
* list where yours is weaker: static seconds, empty panel, caption over a face, object off
  centre, header colliding with an object, punch-in on a soft/wide shot, text too small;
* fix in the template, rebuild, re-render. Write the list + fixes in the reel README.

## 5. Rules

* **Every spoken word gets a seam caption; one word at a time.** Nothing else on screen is
  more than ~5 words (headers 2–4 words).
* Never cover the speaker's face: captions live above the seam; during punch-ins check the
  caption sits below the chin (move `--cap-y` for that clip if not).
* `fromTo` tweens placed late in the timeline paint their FROM state at t=0 —
  use `immediateRender:false` for anything that must stay visible before it (see `SMKit.punch`).
* Deterministic only (no `Math.random`, `Date.now`, network). Generate geometry in `build.py`.
* No template literals inside `querySelector` (the HyperFrames bundler rejects them).
* Free assets only: hand-drawn SVG/CSS with glow, Noto emoji, Openverse/Commons CC. No paid
  image/video generation, no paid APIs.
* Credit the source (license) in the reel README and meta.json. Never commit presigned URLs.
* IG danger zones still apply (top UI y 0–140, bottom UI y ≈1560–1920 is speaker card only,
  right rail x 960–1080): headers start at y 168, captions ≤ 900 px wide.
