# HyperFrame Reel Studio — Agent Operating Brief

This repo turns a **near-ready talking-head video** into a polished vertical reel
(captions + drawn/vector motion + atmosphere) using a config-driven kit.
It runs on the **HyperFrames CLI** (`npx hyperframes@0.6.49`) — HTML + CSS + GSAP,
**not** Remotion. You (the agent) read this file when the repo opens.

## THE FLOW (what the user expects)

> User drops a video into the repo and says *"make me a reel about X"* (Turkish or
> English). You produce a rendered `.mp4` — asking only for what you genuinely need.

When that happens, run the workflow below. **Detailed brief: `kit/AGENT.md`.**

## Workflow (per reel)

1. **Intake** — confirm: the video file path + what it's about + platform (IG Reel /
   TikTok / Shorts). Ask: is there a script, or should you transcribe it? Which theme
   (the user's brand = `kit/themes/nail.css`, or the shareable `kit/themes/fork-sunset.css`)?
   Are any overlays already baked into the video, or left to you? Any image assets (PNG/
   screenshots/logo) to feature? **Ask for these — don't guess.**
2. **New project folder** — `cp -r` the structure of `personal-brand-reel/` (package.json,
   meta.json, hyperframes.json, assets/) into `<your-reel>/`. It's the canonical example.
3. **Encode the source** into `assets/source.mp4` — full-range + padded to 2040 (the extra
   120px is sacrificial, absorbs the renderer's video-bottom drop, cropped away later):
   `ffmpeg -y -i INPUT -vf "scale=1080:1920:flags=lanczos,pad=1080:2040:0:0:black" -c:v libx264 -profile:v high -pix_fmt yuvj420p -color_range pc -r 30 -g 15 -keyint_min 15 -crf 19 -preset slow -movflags +faststart -c:a aac -b:a 192k assets/source.mp4`
   Then PRE-MIX SFX into this audio (see Rules) before rendering.
4. **Measure safe zones** — extract frames at each caption window's midpoint, LOOK at them,
   and place captions where they never cover the speaker's **eyes or mouth**, never collide
   with a baked-in overlay, and stay out of the IG danger zones (below).
5. **Script → captions** — transcribe with **whisper.cpp** if needed
   (`whisper-cli -ojf` for word-level timing; the Python `openai-whisper` CLI can
   segfault on CPU), clean it, then chunk into **3–5 word** on-screen reveals.
   Low text, high image.
6. **Assemble `index.html`** — inline the chosen theme block + caption bands + drawn
   components from `kit/`. Follow the track-index convention and HyperFrames rules below.
7. **`npm run check`** until **0 errors**. Fix everything.
8. **Render** — `npm run render` (outputs 1080×2040), then **crop to the final 1080×1920**:
   `ffmpeg -i renders/<raw>.mp4 -vf "crop=1080:1920:0:0" -c:a copy renders/FINAL.mp4`.
   Verify the output (extract frames at several timestamps, confirm no bottom black band).

## Non-negotiable rules

- **Az yazı, çok görüntü.** 3–5 words on screen; the rest is motion. Never wall-of-text.
- **Never cover the speaker's face/product.** Captions go in dead space (usually the upper
  band over hair/forehead for tight selfies). Full-background cuts ONLY on emphasis beats.
- **Instagram danger zones (1080×1920):** TOP UI `y 0–140` · BOTTOM UI `y ~1560–1920` ·
  RIGHT action rail `x 960–1080, y ~1050–1700`. Keep centered captions ≤900px wide.
  Caption bands live in `kit/captions.css` (`.cap-upper` **470** = over forehead, close to
  the face · `.cap-seg1` 1200 when a baked overlay owns the top · `.cap-mid` 856 · `.cap-lower` 1330).
- **Bottom black band → render TALL + crop.** The renderer intermittently drops the
  bottom ~86px of the VIDEO layer (NOT fixable by encoding/keyframes/CSS scale/atmosphere
  fade — all tested). The fix: author the canvas at **2040** tall (1920 visible + 120
  sacrificial pad), pad the source video to 2040 (`pad=1080:2040:0:0:black`), keep all
  overlays in the top 1920, render, then **crop the output to the top 1920**:
  `ffmpeg -i renders/<raw>.mp4 -vf "crop=1080:1920:0:0" -c:a copy renders/FINAL.mp4`.
- **Source encode = full-range** (`-pix_fmt yuvj420p -color_range pc`). Limited-range
  `yuv420p`/tv worsens the drop. Recipe in step 3.
- **Fonts: Product Sans ("Google Sans") — self-hosted, HAS Turkish (ş ğ İ).** Use it for
  hooks AND captions (one consistent face). cdnfonts woff is live:
  `https://fonts.cdnfonts.com/s/13998/ProductSans-Regular.woff`. ⚠ **Coolvetica has NO
  Turkish glyphs** — dropped for Turkish content (mixing Coolvetica+fallback looks broken).
  Self-host the woff in `assets/fonts/` (Google Fonts `<link>` fails in render).
- **SFX must be PRE-MIXED into the source audio via ffmpeg** (hyperframes barely mixes
  secondary `<audio>` tracks when a main track is present — a 0dB tone vanished in testing).
  Keep the speaker's audio RAW — do NOT de-reverb/process it unless they explicitly ask
  (it sounds worse, not better). Use the USER'S OWN sfx library. Place SPARINGLY and with
  intent: a riser + whoosh on the intro, a riser building into the big reveal/punch (a
  sub-hit riser lands on the key word), a whoosh on scene cuts, and a subtle CLICK on only
  a FEW key text reveals — **NOT on every caption**, and **no electric/flicker zaps**. Bake
  with `adelay` + `atrim`(risers, `LC_ALL=C awk` for dot-decimal) + `volume` +
  `amix=inputs=N:normalize=0` + `alimiter`, output an AUDIO-ONLY file for `#aud`.
- **Deterministic only** — no `Date.now()`, `Math.random()`, or network in the timeline.
- Every timed element: `class="clip"` + `data-start` + `data-duration` + `data-track-index`.
  Timeline `paused` and registered on `window.__timelines["main"]`.
- **AUDIO DOUBLING / echo:** `muted` on `<video>` is NOT respected in render — if `#vid`
  and `#aud` point to the same file with audio, the speech plays TWICE (echo). Give `#vid`
  a **video-only** file (`ffmpeg -i src.mp4 -c:v copy -an video.mp4`) and `#aud` the audio
  file. One audio source only.
- **Track-index convention:** 0 video · 1 atmosphere · 2 full-screen scenes/big text ·
  3 captions · 4 micro drawn overlays · 6 pops · 7 whoosh SFX · 8 audio.

## Themes (drop-in swappable)

Both expose the SAME class contract (`.cool` `.gsans` `.atmo-vig/rim/grain/bot` + glow set),
so swapping ONE theme block re-skins everything:
- `kit/themes/nail.css` — nailingai.co brand ("Reel-tuned": emerald `#10B981` glow + amber
  `#F59E0B`, Product Sans for hooks + captions — Turkish-safe). **Use for the repo owner.**
- `kit/themes/fork-sunset.css` — a distinct public-fork identity ("Sunset Editorial": coral
  `#FB7185` + peach, Cabinet Grotesk + General Sans). **Use when sharing with other people.**

## Map

- `kit/` — the design system: `themes/`, `captions.css`, `components.html` (drawn SVG snippets),
  `anim.js` (HFKit GSAP helpers), `assets/sfx/` (pops), `README.md` (capability menu), `AGENT.md`.
- `personal-brand-reel/` — **canonical example** (an 18s reel). Copy its structure for new reels.
- `nail-ai-reel/`, `nwn-incele-reel/` — older example reels.
- `docs/superpowers/specs/` — the design spec (internal).
- `references/` — reference videos/frames.

## Commands (per reel folder)

`npm run dev` (long-running preview server — run in background) · `npm run check` (lint +
validate + inspect; fix all errors) · `npm run render` (→ `renders/*.mp4`) · `npm run publish`.
