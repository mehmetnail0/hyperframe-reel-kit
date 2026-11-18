# Kallaway music beds — what he uses, where to get it

Measured on his 20 latest reels (2026-10-29 → 11-18). Method: demucs removes the voice,
then 4 × 14 s windows of the music stem per reel go to the free Shazam endpoint (`shazamio`,
`research/tools/music_id.py`). No audio was downloaded or committed, only metadata.

## Identified tracks

| track | artist | reels | Shazam | ISRC | measured |
| --- | --- | --- | --- | --- | --- |
| **Bubbles Drop** | Cosmonkey (Aleksandr Shepelev) | **14 / 20** (13 matched 3–4 of 4 windows, 1 matched 2) | https://www.shazam.com/track/692635430/bubbles-drop (alt. listing https://www.shazam.com/track/850365018/cosmonkey-bubbles-drop) | USCGJ2431556 | 129 BPM, D♯/E♭ major, bright plucks + soft sidechained pad, light hats; "digital-sweet" |
| **cdHiddenDir** | Out of Flux | **3 / 20** (DfzlY0XMeeN, Df4rQ4IM-S1, DfFWzxGxWWH; 4 of 4 windows each) | https://www.shazam.com/track/625979038/cdhiddendir | IL6652204061 | ~117 BPM, F/G minor, glassy arps, darker and calmer |

**Where to get them (license / buy yourselves):** both are on the usual streaming catalogues
(search title + artist on Spotify / Apple Music to confirm the version). For a commercial reel
you need a sync licence, not a stream: check the artist's distributor/label page from the
Shazam link, a stock library that carries the artist (search "Cosmonkey" / "Aleksandr
Shepelev" / "Out of Flux" on Artlist, Epidemic Sound, Envato/AudioJungle, Pond5), or use the
track from Instagram's own audio library when posting natively (then it is licensed only
inside Instagram — do not bake it into the exported mp4). ISRCs above identify the exact recordings.

## Unidentified (3 / 20) — describe to find similar

| reel | tempo / key | bed vs voice | vibe |
| --- | --- | --- | --- |
| Df2E7aDsFCZ (motion reference "transpositioning") | 129 BPM, D♯ major | −16 dB | same family as Bubbles Drop (same tempo/key; Shazam failed under heavy SFX) — likely an edit/stem of it |
| DfUhxJqxLxP | 144 BPM, A♯ major | −18 dB | quick, light, plucky; percussive top end |
| DfsP1jSsdjn | 108 BPM, E minor | −22 dB | very low, dark-ish pad bed, barely there |

Search terms that land in the same pocket: *"future bass pluck 128 bpm bright"*, *"tech
vlog bubbly electronic"*, *"digital pluck background corporate playful"*, *"glassy arp
minimal electronic 115 bpm"*.

## How the bed sits (all 20 reels)

* **Every reel has a bed.** Level of the bed (music stem outside SFX events) vs the voice's
  active level: median **−16.9 dB** (IQR −18.2 … −15.5; range −22 … −10).
* It mostly *starts lower under the hook*: in 15 / 20 reels the 2-s level curve drops 6+ dB
  somewhere in seconds 4–10 (the music comes in under the hook and sits back while the
  framework is introduced), then swells toward the middle/end; very few hard stops.
* Tempo: 129 BPM in 11 / 20 (86 BPM in 3 is the same track read at 2/3), 103–144 in the rest.
* One track is reused across most reels: the bed is a **brand constant**, the SFX and motion change.

## In the harness

`sfx_mix.py mix ... --music BED.wav` (or `run.py --music BED.wav`) lays a licensed bed at
**−17 dB under the voice** (the Kallaway median), fades in 0.6 s / out 1.2 s, and ducks it
with the speech (sidechain, 3:1). The proof reels ship **without** music (no licence for
these tracks here); add yours and re-run only step 4 (`--plan data/plan.json`).
