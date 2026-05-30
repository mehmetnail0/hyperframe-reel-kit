# AGENT.md — Agent-Assisted Reel-Overlay Console

This is the operating brief for the **agent-assisted console**: a person drops in
a near-ready video, and you (the agent) prepare their reel overlays — captions,
drawn motion, atmosphere — asking for exactly what you need along the way. This is
the fork vision: hand it to other people with `fork-sunset.css` as their default
identity.

You are not a passive renderer. You read the script, pick the visual language,
measure the frame, and assemble the composition. **Az yazı, çok görüntü.**

---

## 1. Intake — ask these in order

Ask one batch, wait for answers, don't assume:

1. **Video + context** — the video file path, what it's about, and target platform
   (IG Reel / TikTok / Shorts). Platform sets the safe-zone map (this kit defaults
   to IG 1080×1920 danger zones).
2. **Script / captions** — is there an existing script or caption file, or should
   you transcribe it? If transcribe → **whisper.cpp** (`whisper-cli -ojf` for
   word/token-level offsets), then clean. Prefer whisper.cpp over the Python
   `openai-whisper` CLI: the latter can **segfault on CPU** (seen on macOS, every
   model size). Turkish ASR garbles some words → re-read, correct, and flag the
   1–2 you can't be sure of to the user before baking them into captions.
3. **Theme** — their own brand tokens, or a preset (`fork-sunset` is the default
   public identity; `nail` is reserved for nailingai). If brand: get colors + fonts.
4. **Baked vs. open** — which overlays are ALREADY burned into the video (e.g. a
   diagram covering the top, a name lower-third) vs. left to you. This decides
   caption bands: a baked top overlay → use `.cap-seg1` (top:1200), not `.cap-upper`.
5. **Image assets** — any PNG / screenshots / logos to feature on screen (for
   circle-mask photo, badges, full-bg punch scenes). Ask up front; don't invent.

---

## 2. Workflow

| Step | Action |
| --- | --- |
| 1. Probe | `ffprobe` the video — duration, resolution, fps. Confirm 1080×1920 (or plan a fit). |
| 2. Frames | Extract frames at each caption-window midpoint (where text will sit in time). |
| 3. **Measure safe zones** | On those frames, locate mouth/eyes and any baked overlay. Choose the caption band per window so text NEVER covers face/baked-overlay and respects IG danger zones (top 0–140, bottom 1560–1920, right rail x960–1080 / y1050–1700). |
| 4. Script | Transcribe (Whisper) if needed, then clean — fix punctuation, drop filler. |
| 5. Chunk | Break captions into **3–5 word** reveals timed to speech. Short, punchy. |
| 6. Theme | Apply the chosen theme: paste its `<head>` block, inline its `<style>`. |
| 7. Assemble | Build `index.html` using the track-index convention (0 video · 1 atmosphere · 2 scenes/big text · 3 captions · 4 micro/camera frame · 6 pop sfx · 7 whoosh/transition sfx · 8 audio). Pull SVG snippets from `kit/components.html`, helpers from `kit/anim.js` (`window.HFKit`). |
| 8. Check | `npm run check` (lint + validate + inspect). Fix all errors before showing. |
| 9. Iterate | Snapshot key frames, re-measure, adjust bands/timing, repeat. |

Caption band reference (from `kit/captions.css`): `.cap-upper` 160 (default tight
selfie) · `.cap-mid` 856 (split/empty mid) · `.cap-lower` 1330 (chin clear only) ·
`.cap-seg1` 1200 (under baked top overlay).

---

## 3. Hard rules

- **Az yazı / çok görüntü** — 3–5 words on screen, the rest is motion.
- **Never cover the speaker's face or the product.** Measure before placing.
- **Full-background cuts only on emphasis beats** — a single big idea, then whip
  back to the speaker. Not as filler.
- **Deterministic only** — no `Date.now()`, no `Math.random()`, no network at runtime.
- **Always run `npm run check`** before presenting. Errors block delivery; review
  inspect warnings before render.
- One theme `<style>` block live in the composition; swapping it re-skins everything.

### Render checklist — DO NOT skip (validated on hyperframes@0.6.49)

1. **`.atmo-bot` bottom fade is MANDATORY.** Include `<div class="atmo-bot"></div>`
   as the LAST child of the atmosphere layer in EVERY composition. The renderer
   intermittently drops the bottom **~86px of the VIDEO layer** (a per-seek-time
   artifact — NOT fixable by source encoding, keyframes, or CSS scale; all tested).
   Regular DIVs paint to the bottom fine, so the near-opaque bottom gradient masks
   the black band, reads as an intentional cinematic vignette, and sits in the IG
   bottom-UI zone anyway. Both themes ship it (`.atmo-bot`).

2. **Encode the source video full-range.** Limited-range (`yuv420p` / tv) causes
   WORSE bottom-drop. The source MUST be full-range (`yuvj420p` / `color_range pc`).
   Downscale to the 1080×1920 render target with dense keyframes for clean seeking:

   ```bash
   ffmpeg -y -i INPUT \
     -vf "scale=1080:1920:flags=lanczos" \
     -c:v libx264 -profile:v high -pix_fmt yuvj420p -color_range pc \
     -r 30 -g 15 -keyint_min 15 -crf 19 -preset slow \
     -movflags +faststart -c:a aac -b:a 192k \
     assets/source.mp4
   ```

3. **Light "pıt" pops on overlay/caption pop-ins.** Use `kit/assets/sfx/pop.wav`
   (soft ~920 Hz) for normal caption/overlay reveals and `kit/assets/sfx/pop_hi.wav`
   (sharper ~1320 Hz) for accents (e.g. an X-strike). Place pops on a **dedicated
   audio track-index SEPARATE from whoosh/transition SFX** — pops on **track 6**,
   whooshes on **track 7**, main audio on **track 8**. ⚠ hyperframes ERRORS on
   overlapping clips on the SAME track, so never mix pops and whooshes on one track.

4. **Fonts must be SELF-HOSTED** (`.woff` / `.woff2` in `assets/fonts`). Google
   Fonts `<link>` tags fail in render — only use them for PREVIEW. ⚠ Coolvetica
   has **NO Turkish glyphs** — `ş/ğ/İ` fall back to the body font (Plus Jakarta
   Sans on `nail`); pick a Turkish-capable display font for Turkish hooks.

5. **`npm run check` must report 0 errors** before declaring the job done.

6. **Always show the user a CROPPED preview** (1080×1920), never the raw 2040-tall
   render — the sacrificial pad reads as a "black band / deleted frame" and gets
   flagged. Verify caption placement from a draft render (contact sheets at each
   caption midpoint), fix collisions, THEN do the `standard`/`high` final.

7. **Dense already-edited reaction reels** (collage walls, reference clips with
   their own baked captions, screen-shares, a baked payoff card): the job is
   **SFX-primary + captions ONLY on the user's still-uncaptioned narration**. Don't
   re-caption sections that already carry baked text — "don't break existing work."
   Lower band (chest) by default; chip ONLY over bright screens; one rare drawn
   accent on the CTA, never over a close-up face.

8. **Appended outro / extra clip** → build it as a **standalone captioned
   composition** (`extra.html`, render with `-c extra.html`), crop to 1920, then
   `ffmpeg` concat after the main with a soft whoosh bridge at the seam. Ship both
   the base version and the appended version when asked.

---

## 4. Proactively ask for

When the script or video leaves you guessing, stop and ask — don't fabricate:

- **Image assets** — PNG / screenshots / logos for any photo-mask, badge, or
  full-bg punch scene you want to use.
- **Exact wording** — for any ambiguous or inaudible line before baking it into a caption.
- **Brand colors / font** — if "their brand tokens" was chosen but not provided
  (otherwise default to `fork-sunset`).
- **Which lines are emphasis beats** — so full-bg cuts land where they intend, not
  where you guessed.
