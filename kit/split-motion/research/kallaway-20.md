# Kallaway — 20 latest reels, measured (2026-10-29 → 11-18)

Raw data: [`kallaway-20.json`](kallaway-20.json) (per reel + summary) · music: [`music.md`](music.md) ·
tools: [`tools/`](tools/) (all re-runnable; the reels themselves are not in the repo).

## Headline numbers

| | value (median, IQR) |
| --- | --- |
| **SFX per minute** (synced to picture, conservative) | **18.0** (15.3–21.7); hook **26**/min, body **17.5**/min, CTA **14**/min |
| SFX per minute, loose upper bound (incl. some music hits) | 37 (30–44) |
| **type mix** (synced) | **pops/ticks 55 %** · **light risers 22 %** · low swells 13 % · glows/shimmers 8 % · other 2 % |
| **risers** | **3.9 / min** (3.2–5.9) synced to a reveal/cut — DfzlY0XMeeN: 6 in 39 s; Dfx2dzvuI2V: 14 candidates, 7 synced |
| level vs voice (event peak vs voice active RMS) | risers −8 dB · glows −8 · pops −14 · low swells −14.5 · tiny ticks −26 |
| gap between SFX | 2.3 s median; 10th pct 0.2 s (= the "pıt pıt" double/triple ticks) |
| same sound back-to-back | ~1 per reel (practically never); same *type* back-to-back 37 % (mostly tick runs) |
| **music bed** | in **20/20** reels, **−16.9 dB** under the voice (−18.2 … −15.5); one track in 14/20 (Bubbles Drop — Cosmonkey) |
| layout | **split 71 %** · full-screen speaker **29 %** (runs 3.0 s, 1.9–4.8) · full graphic ~0 (2/20 reels) |
| layout switches | **8.7 / min**; a speaker run every **10.4 s** (7–14) |
| panel changes | **58 / min** (37–67): something changes every ~1 s; median gap 0.3 s |
| hook | first sentence **3.6 s** (3.2–4.2): "Here's how to…", "This is the ultimate…", "These are the only N…" |
| CTA | "Comment 'X' to get…" in **19/20**, **6.9 s** before the end |
| pace | 229 wpm |

How to read the SFX numbers: demucs leaves a little music percussion in the residue, so a
detected event only counts as an SFX when a frame change lands on it (the editor syncs SFX
to the cut; music hits only do that by chance, ~24 %). Detected events land on picture
changes 44 % of the time vs 24 % chance; risers 52 % at their peak. Counts are ± ~25 %,
categories are from spectral shape (no ear check).

## Per reel

| reel | date | dur s | split/speaker/graphic % | switches | SFX/min synced (loose) | risers | pops+ticks | bed dB | BPM / key | track |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Df4rQ4IM-S1 | 11-18 | 92 | 84/16/0 | 10 | 15.0 (21.6) | 6 | 13 | −13.8 | 112 / F minor | cdHiddenDir |
| Df2E7aDsFCZ | 11-17 | 83 | 74/26/0 | 8 | 15.2 (29.7) | 8 | 10 | −16.3 | 129 / D♯ major | — |
| **DfzlY0XMeeN** | 11-16 | 39 | 71/29/0 | 7 | 13.9 (21.6) | 6 | 2 | −16.4 | 118 / G minor | cdHiddenDir |
| **Dfx2dzvuI2V** | 11-15 | 109 | 80/20/0 | 15 | 21.0 (40.3) | 7 | 21 | −16.0 | 103 / D♯ major | Bubbles Drop |
| DfvW02auTpj | 11-14 | 91 | 68/32/0 | 12 | 23.0 (42.0) | 6 | 17 | −17.4 | 129 / D♯ major | Bubbles Drop |
| DfsP1jSsdjn | 11-13 | 136 | 77/23/0 | 30 | 18.5 (27.7) | 6 | 26 | −22.3 | 108 / E minor | — |
| DfpJ4UOMfkn | 11-12 | 124 | 83/17/0 | 14 | 16.4 (34.3) | 6 | 15 | −17.9 | 86 / C♯ major | Bubbles Drop |
| DfmjvZ4MN6e | 11-11 | 101 | 66/34/0 | 20 | 25.0 (44.0) | 11 | 24 | −17.1 | 86 / D♯ major | Bubbles Drop |
| DfkAT7Fxpm6 | 11-10 | 119 | 69/31/0 | 16 | 20.6 (39.7) | 8 | 22 | −10.5 | 129 / D♯ major | Bubbles Drop |
| Dfh3VKaMteH | 11-09 | 130 | 81/19/0 | 16 | 15.7 (34.7) | 8 | 21 | −16.9 | 86 / C♯ major | Bubbles Drop |
| DffZRmfMWrf | 11-08 | 56 | 70/30/0 | 13 | 26.8 (46.1) | 3 | 17 | −9.6 | 129 / D♯ major | Bubbles Drop |
| Dfc59rPsETD | 11-07 | 77 | 59/40/2 | 16 | 24.3 (48.5) | 7 | 19 | −18.3 | 129 / D♯ major | Bubbles Drop |
| DfZmV6px5n3 | 11-06 | 57 | 73/27/0 | 8 | 18.0 (46.6) | 3 | 10 | −15.5 | 129 / D♯ major | Bubbles Drop |
| DfXMwncxfPu | 11-05 | 98 | 57/39/4 | 21 | 12.3 (29.5) | 2 | 14 | −19.9 | 129 / D♯ major | Bubbles Drop |
| DfUhxJqxLxP | 11-04 | 67 | 13/57/30 | 23 | 17.9 (35.8) | 5 | 8 | −18.1 | 144 / A♯ major | — |
| DfR434rRxcI | 11-03 | 127 | 60/40/0 | 25 | 29.7 (44.3) | 13 | 37 | −15.5 | 129 / A♯ minor | Bubbles Drop |
| DfPXiP0RhNl | 11-02 | 33 | 70/30/0 | 4 | 18.0 (32.4) | 4 | 5 | −21.4 | 136 / C minor | Bubbles Drop |
| DfN6UEfuvQZ | 11-01 | 99 | 69/31/0 | 14 | 21.3 (43.7) | 5 | 19 | −18.3 | 129 / D♯ major | Bubbles Drop |
| DfHxna7R17Q | 10-30 | 88 | 73/27/0 | 15 | 15.0 (38.2) | 5 | 13 | −16.8 | 129 / D♯ major | Bubbles Drop |
| DfFWzxGxWWH | 10-29 | 102 | 72/28/0 | 15 | 15.3 (21.2) | 12 | 12 | −10.9 | 118 / F minor | cdHiddenDir |

(86 BPM = the 129 BPM track read at 2/3 tempo. Light "grid paper" theme: DffZRmfMWrf 63 % of
its split time, DfXMwncxfPu 65 %, DfUhxJqxLxP 76 %, DfsP1jSsdjn 26 %; the rest are dark.)

## Sound — what happens and where

* **Risers (Nail's "sürekli riser")** are short (1.7–3.9 s) light swells that **peak exactly on
  a layout switch, a panel build or a cut** (DfzlY0XMeeN: 1.1 → peak 3.1 at the first cut,
  3.6 → 5.7 at the switch to full speaker, 8.4 → 9.8 back to the panel, 18.2 → 21.9 and
  22.3 → 25.7 under the doc building, 30.2 → 32.5 at the CTA cut). They are loud-ish
  (−1 … −9 dB vs voice) but soft-edged: no transient, all swell. **Dfx2dzvuI2V** (the riser
  reference) opens with one at 0.0 → 1.3 s, then lays one under each of the hook levels
  (45 → 46.7, 54 → 55, 67 → 70, 76, 83 s) — roughly every 8–10 s in the body.
* **Pops/ticks (the "pıt pıt pıt")**: the majority sound. Tiny, mid-pitched (centroid 300–600 Hz,
  ~0.1 s), in **pairs or triples 0.15 s apart** on list rows, counters and chips appearing
  (Dfx2dzvuI2V 42.9/43.1, 52.4/52.6, 56.1/56.3/56.5, 92.9/93.0 s). −10 … −22 dB under the voice.
* **Glows/shimmers**: on a hero landing (phone, doc, logo), 0.5–0.8 s, ~−8 dB; a few per reel.
* **Low swells/booms**: under the hook and on the biggest cut, felt more than heard.
* **Flash/shine**: a bright "shing" with a white flash frame at most 1–2 times a reel — never twice in a row.
* **Repetition**: the same sample back-to-back ~once per reel; tick runs are the only place
  one category repeats immediately (and even there the pitch/sample alternates).
* **Flow**: densest on the hook (26/min: riser + whoosh + ticks while the header types),
  steady in the body (17.5/min, one riser into each new step/level), a riser + tick or two on
  the CTA. The music sits back under the hook (in 15/20 reels its level dips 6+ dB in s 4–10)
  and comes up as the framework unfolds.

## Motion and text (frame sheets at 2 fps + frame-diff timelines at 10 fps)

**Layout.** Split = top panel y 0–1370 on near-black (or light grid paper) with a faint
square grid; seam caption at y ≈ 1258; speaker card y ≈ 1373–1900 (a wide ~1.9:1 crop, the
speaker waist-up), rounded corners. Full-screen speaker interludes (29 % of the time, ~3 s,
every ~10 s) carry a bigger caption mid-low. Full-screen graphics are rare (DfUhxJqxLxP is
the exception: a light "template" deck).

**Header.** 1–2 lines at the top, bold geometric sans + one **serif-italic** word
("The Ultimate *Scriptwriting Format*", "How To Find Unused *Content Formats* In Your Niche"),
often a phrase in a **red highlight box** ("Text Hook", "Fresh formats", "In Less Than 5
Months"), or a short red underline. It types on word by word with the hook and stays for the section.

**Hero devices (seen across the 20):** document card with **colour-coded highlighter
lines** building row by row (Hook / Body block / Rehook / CTA); **orbit** of thumbnail cards
around a red pill on a dashed circle; **numbered rows 01–05** whose unrevealed rows are
**blurred**; **phone mockups** with a red headline ("6 Words / To Hook Any Viewer");
thumbnail **grids/collages** with one highlighted; **branch trees** (Level 1 → 01, 02);
**radar rings** with red dots; **network** of avatars with a counter chip ("213.1K");
browser / YouTube player cards; comment-CTA with **stacked document pages**; logos joined by "+".
Entrances: pop/scale with overshoot, rise, slide; exits: quick blur/scale or whip.

**Cadence.** The panel changes ~58×/min; a new hero every ~1.5–3 s, sub-events in between
(row reveal, highlight, count). The "1-2-3" device is a numbered list or chapter number
revealed on the spoken word, each step with a tick (single) or a riser (new chapter).

**3D.** Not literal 3D renders but 3D-feeling moves: tilted phone/cards in perspective,
parallax push-ins, orbiting card rings. (devinjatho goes further with real 3D objects.)

### DfzlY0XMeeN — the motions Nail wants
39 s, 7 layout switches. Opens on a **document card** ("Video Script") under a two-line
header (bold sans + serif "Scriptwriting Format", red underline) → the doc shrinks into the
centre of a **red glowing circle** while six reel thumbnails orbit it (2–4 s) → back to the
doc which **builds row by row** with coloured highlighter bars as he names each block
(Hook, Lock-in zone, Body block 1, Rehook 1 …, 9–19 s and 22–29 s) → a **collage grid**
("Works For Any Niche / Drives Views & Leads", red box) → **stacked document pages** for the
CTA. Full-screen speaker runs of 2–4 s between. SFX: 6 risers each peaking on a switch/build,
almost no ticks. **Lesson: one hero object that keeps evolving + a riser per evolution.**

### Dfx2dzvuI2V — the risers Nail wants
109 s, 80 % split. Header "Ultimate *Text Hook* Guide" (red box) → orbit of hook examples →
phone "6 Words / To Hook Any Viewer" → reel grid → blurred **01–05 rows** revealed one by one
(ticks) → "Level 1 → 01 Substance / 02 Design" tree → phone with tool grid → "Comment 'Text'".
14 riser candidates (7 visually confirmed) ~every 8–10 s, pops in pairs on every row/chip,
glows on the phone landings.

## Flow (hook → body → CTA)

1. **Hook 3–4 s**: claim + named framework; header types on; riser + low swell + 2–4 ticks.
2. **Framework intro**: the hero device appears whole (orbit / doc / phone), then the speaker card.
3. **Body**: 3–6 steps; each = row/chapter revealed on the word (tick), a full-screen speaker
   punch every ~10 s on the opinion lines, a riser into each new level.
4. **Proof**: a collage/grid or a number counter ("I have 2M followers…").
5. **CTA 6–8 s before the end**: "Comment 'WORD'…" + stacked pages / phone; riser + ding.

## Kallaway grammar (rules with numbers) → used by the harness

| rule | number | where enforced |
| --- | --- | --- |
| SFX density | **16/min** target (Kallaway 18, made a touch "efendi") — hook ~1.5× denser | `sfx/engine.py --per-min`, intro cues |
| type mix | ~50 % soft ticks/pops · ~20 % light risers · ~15 % whooshes/low swells · ≤10 % glows · flash ≤ 2/reel | engine role→category map + caps |
| risers | **3–5 / min**, always **peak-aligned** on a reveal / chapter / layout switch | engine `align: peak`; compiler emits `chapter`/`reveal`/`punch` cues |
| ticks | runs of 2–3, 0.12–0.2 s apart on rows/counters; files alternate inside a run | engine counter runs |
| repetition | same file never back-to-back; same category only inside a tick run | `engine.check()` (QC) |
| levels (vs voice) | risers/glows −12/−13, whooshes −14/−15, ticks −18, draws −20 (Kallaway −8/−8/−14/−26, softened ~4 dB) | `sfx/palette.json` under_voice_db |
| music | bed −17 dB under the voice, ducked by speech; dips under the hook | `sfx_mix.py --music` |
| layout | split ~70 %; speaker runs 1.5–4 s every 7–14 s; graphic ≤ 1 beat | planner prompt + validation |
| cadence | one hero per 1.5–3.5 s beat + sub-events; never > 3 s static | planner prompt; `qc.motion` |
| hook | first sentence ≤ 4 s, header types on with it | planner prompt |
| text | header ≤ 2 lines, one serif-italic accent, red box or underline; caption 1–3 words | `kw.css`, compiler |
| CTA | "Comment 'X'" 5–8 s before the end when the speaker says it | planner (`cta` scene) |
