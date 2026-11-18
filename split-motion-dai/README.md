# split-motion-dai

Proof reel for the **split-motion** style (`kit/split-motion/`): a raw 4K 16:9 two-person
podcast clip (86 s, multicam) cut into a 67 s English vertical reel. The top panel carries
the motion, the bottom card holds the speaker, there's a one-word seam caption on every
spoken word, four chapter fly-ins through a recurring device (the red **PREP RING**), five
full-screen punch-ins, and a recap ending.

**Credit:** Footage from *Dai By Dai Podcast*, "The #1 Thing Holding Back Content Creators"
(YouTube `HopW8EtFF8A`), licensed **CC-BY**. Edited into a vertical reel; the motion
graphics (hand-written SVG/CSS) and the SFX (synthesised by `kit/split-motion/sfx/make_sfx.py`)
are original. The corner "DAXON" logo is cropped out of every shot.

Output: `renders/FINAL.mp4` (1080×1920, 30 fps, −14 LUFS) · `renders/sheet.jpg` (2 fps contact sheet).

## Story cut (65.3 s of speech + 2 s recap)

instant gratification (money, attention, followers) → people ask me for a shout-out, I say
no: you don't have the catalog → keep dropping, be consistent → when opportunity meets
preparation, fireworks happen → a contract at your door: do you need an entertainment
lawyer? → you're on step zero and you should be on step A.

Every cut boundary sits inside a measured energy dip. The cut audio was re-transcribed
to confirm that no word is clipped (see `scripts/edit.py`).

## Beat sheet (panel)

| t (s) | header | hero object / event |
| --- | --- | --- |
| 0.1–6.2 | instant *gratification* | phone, follower counter races 0→48,920, bars grow, hearts/$ float · 3.4 phone slides left, gold coin list: money / attention / followers |
| 6.2–9.7 | they want it *now* | chart: green curve shoots up ("want it now") → red flat line ("don't get it now") → **STOP** sign slams in |
| 9.8 | — | **chapter 1 · the shout-out** (fly into the ring) |
| 11.1–15.6 | can you *shout me out?* | DM: typing → "hey, can you shout me out?" · *punch-in "I say no. Why?"* · reply bubble **no.** · "ready for a shout-out 12%" bar |
| 15.8 | — | **chapter 2 · preparation** |
| 17.1–21.0 | no *catalog*, no shout-out | megaphone + waves + "+ shout-out" chip → users flow into "your page" along connector lines |
| 21.0–23.1 | | *punch-in "then what? They don't have nothing to watch"* |
| 23.1–27.0 | | 3×3 grid with only **2 posts** → "nothing to watch" vs **the catalog** grid filling |
| 27.0–29.6 | | *punch-in "You're not prepared. You don't have the catalog."* |
| 29.6–32.9 | keep *dropping* | 28-day streak calendar ticks green + counter → post cards #1…#30 deal into a fan |
| 32.9 | — | **chapter 3 · the moment** |
| 34.1–36.2 | opportunity meets *preparation* | OPPORTUNITY (gold) and PREPARATION (green) orbs slide in, line draws, they collide (riser) |
| 36.3–37.9 | | **fireworks**: three bursts (rays and particles) + BOOM |
| 37.9–40.3 | | hourglass ("the opportunity will come") · *punch-in "you just gotta wait"* |
| 40.3–46.2 | the wrong *order* | first/then track: OPPORTUNITY jumps ahead of PREPARATION → red ✕ → big serif "?" with orbiting dots |
| 46.2–48.7 | | *punch-in "you don't even know how to handle that level…"* |
| 48.7–51.6 | a whole new *level* | LVL meter 1→99 → message: "hey, I got a contract for you right now" |
| 51.6–58.9 | the *contract* moment | wireframe CONTRACT, lines draw, signature line · "who to look at?" avatars · clauses highlighted red with "?" · scales icon "entertainment lawyer?" + connector |
| 58.9–60.3 | | coin list: the terms ✕ / who to call ✕ / a lawyer ✕ |
| 60.4 | — | **chapter 4 · step zero** |
| 61.7–65.3 | step zero → step *A* | neon stairs draw, red dot "step 0", spotlight cone and dashed path to the top step **A** |
| 65.3–67.3 | preparation meets *opportunity* | recap: the ring with all four chapter labels |

## Rebuild

```bash
# 0. tools: whisper.cpp (whisper-cli) + ggml-small.en.bin, ffmpeg, node 22
# 1. transcript of the raw clip (word level)
whisper-cli -m ggml-small.en.bin -f raw16k.wav -ojf -of scripts/whisper_words -ml 1 -sow
# 2. story cut + speaker video (writes data/edl.json, WORK/speech.wav, WORK/base.mp4)
python3 -I scripts/edit.py RAW.mp4 WORK
# 3. verify the cut and get caption timings from the CUT audio
ffmpeg -i WORK/speech.wav -ac 1 -ar 16000 WORK/cut16.wav
whisper-cli -m ggml-small.en.bin -f WORK/cut16.wav -ojf -of WORK/cut_words -ml 1 -sow --dtw small.en -nfa
python3 -I scripts/captions.py WORK/cut_words.json WORK/cut16.wav     # -> data/words.json
# 4. media: video-only + SFX pre-mix (-14 LUFS)
ffmpeg -i WORK/base.mp4 -c:v copy -an assets/video.mp4
python3 -I ../kit/split-motion/sfx/make_sfx.py
python3 -I scripts/mix.py WORK/speech.wav assets/mix.wav
# 5. composition, check, render, crop
python3 -I scripts/build.py && npm run check
npm run render -- -o renders/raw.mp4
ffmpeg -i renders/raw.mp4 -vf "crop=1080:1920:0:0" -c:v libx264 -crf 18 -c:a copy renders/FINAL.mp4
# 6. QC
python3 -I scripts/qc_motion.py renders/FINAL.mp4
scripts/sheets.sh renders/FINAL.mp4 REF.mp4 renders
```

Files: `src/template.html` (markup + beat timeline) → `scripts/build.py` → `index.html`
(inlines `kit/split-motion/split-motion.css` + `sm-anim.js`, generates captions and the
repeated SVG geometry). `assets/video.mp4` and `assets/mix.wav` are regenerated, not committed.

## Review rounds (ours vs reference, 2 fps sheets + `scripts/qc_motion.py`)

| | round 1 | round 2 | round 3 (FINAL) | reference |
| --- | --- | --- | --- | --- |
| static runs > 3 s (panel) | 0 | 0 | **0** (longest 0.7 s) | 0 (longest 0.8 s) |
| major panel changes | 104 (1 / 0.65 s) | 131 (1 / 0.51 s) | **134 (1 / 0.50 s)** | 154 (1 / 0.60 s) |
| longest gap between major changes | 5.3 s | 3.9 s | 3.9 s* | 5.4 s |

\* 23.2–27.0 s: 2-post grid → "vs the catalog" grid → green fill. Things keep moving, but the
dark tiles change less than the metric's threshold.

**Round 1 → fixes.** Before the first punch-in the panel was missing and a grey veil
covered the frame (`fromTo` immediate-render on the punch tweens → `immediateRender:false`
in `SMKit.punch`). Hero objects were ~30% smaller than the reference's, so each stage got
its own scale. Long sub-event gaps (contract 5.3 s, megaphone/grid 3.9 s, stairs 3.8 s,
order 3.4 s, phone 3.3 s) got push-ins, a megaphone swing, a contract zoom and a counter zoom.
The wide-shot crop was too loose (1680 → 1360 px). The spotlight cone read as a flat grey
triangle (now a halo with beam lines). The header comma spacing was off.

**Round 2 → fixes.** The stairs were still a 3.8 s gap (camera now pans to step 0, then to step A).
The "2 posts" chip collided with the seam caption (moved onto the grid). The return flash after
a punch-in read as a grey frame (0.35 → 0.18). The catalog grid entrance was too faint (whip
in, then a green fill). A few objects grew into the header/caption after scaling (zooms toned
down, hero frame 1000 px wide so drift stays inside the panel).

**Still different from the reference:** no real b-roll inside cards (the reference cuts to
other footage and photo-real objects such as a slot machine, cards, and a price-chip phone;
ours is all hand-drawn line art); no speaker head popping out of the card (the reference
segments the speaker over the seam); one full-screen B-roll moment is missing (no free
footage that fits); during host-camera multicam cuts the bottom card shows the listener.
