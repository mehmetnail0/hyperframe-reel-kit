# CLAUDE-arsiv

## Moved from CLAUDE.md 2026-10-03

**not** Remotion. You (the agent) read this file when the repo opens.

## THE FLOW (what the user expects)

> User drops a video into the repo and says *"make me a reel about X"* (Turkish or
> English). You produce a rendered `.mp4` — asking only for what you genuinely need.

When that happens, run the workflow below. **Detailed brief: `kit/AGENT.md`.**

1. **Intake** — confirm: the video file path + what it's about + platform (IG Reel /
   TikTok / Shorts). Ask: is there a script, or should you transcribe it? Which theme
   (the user's brand = `kit/themes/nail.css`, or the shareable `kit/themes/fork-sunset.css`)?
   Are any overlays already baked into the video, or left to you? Any image assets (PNG/
   screenshots/logo) to feature? **Ask for these — don't guess.**

- **Bottom black band → render TALL + crop.** The renderer intermittently drops the
  bottom ~86px of the VIDEO layer (NOT fixable by encoding/keyframes/CSS scale/atmosphere
  fade — all tested). The fix: author the canvas at **2040** tall (1920 visible + 120
  sacrificial pad), pad the source video to 2040 (`pad=1080:2040:0:0:black`), keep all
  overlays in the top 1920, render, then **crop the output to the top 1920**:
  `ffmpeg -i renders/<raw>.mp4 -vf "crop=1080:1920:0:0" -c:a copy renders/FINAL.mp4`.
- **Source encode = full-range** (`-pix_fmt yuvj420p -color_range pc`). Limited-range
  `yuv420p`/tv worsens the drop. Recipe in step 3.

  secondary `<audio>` tracks when a main track is present — a 0dB tone vanished in testing).
  Keep the speaker's audio RAW — do NOT de-reverb/process it unless they explicitly ask
  (it sounds worse, not better). Use the USER'S OWN sfx library. Place SPARINGLY and with
  intent: a riser + whoosh on the intro, a riser building into the big reveal/punch (a
  sub-hit riser lands on the key word), a whoosh on scene cuts, and a subtle CLICK on only
  a FEW key text reveals — **NOT on every caption**, and **no electric/flicker zaps**. Bake
  with `adelay` + `atrim`(risers, `LC_ALL=C awk` for dot-decimal) + `volume` +
  `amix=inputs=N:normalize=0` + `alimiter`, output an AUDIO-ONLY file for `#aud`.

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

- `nail-ai-reel/`, `nwn-incele-reel/` — older example reels.
- `docs/superpowers/specs/` — the design spec (internal).
- `references/` — reference videos/frames.
