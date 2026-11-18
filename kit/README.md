# HyperFrames Reel-Overlay Kit

A **config-driven reel-overlay system** for 1080×1920 vertical video. You bring a
near-ready talking-head video; the kit gives you IG-safe captions, drawn/vector
motion, full-background interstitials, and an always-on atmosphere layer — all as
copy-paste HTML/CSS/GSAP that runs inside a **HyperFrames** single `index.html`
composition (`npx hyperframes@0.6.49`, **not** Remotion).

## Ne işe yarar

- **Tek tema dosyası değiştir → tüm reel yeniden skinlenir.** Theme dosyaları
  (`kit/themes/nail.css`, `kit/themes/fork-sunset.css`) aynı class kontratını
  açar (`.cool`, `.gsans`, `.atmo-*`, glow set). Composition markup'ı sabit kalır,
  sadece `<style>` bloğunu swapla.
- Az yazı, çok görüntü. Altyazılar her zaman IG'nin UI'ı ve yüzün dışında durur.
- Deterministik: `Date.now`/`Math.random`/network yok → her render birebir aynı.

## Sana çıkaracağım iş tipleri

| Tetik (sen dersin) | Çıkan iş |
| --- | --- |
| "Hazır video, sadece altyazı koy" | IG danger-zone-aware caption yerleşimi — yüzü/baked overlay'i ASLA kapatmaz; chunked kısa reveal'lar, az yazı (3–5 kelime) |
| "Bu sahnede şu anlatılıyor" | Drawn/vector motion — stroke-draw ok, circle-mask foto, radial hub, comparison split, counter/badge |
| "Sahne aralarına nefes" | Full-background interstitial sahne — konuşmacıyı kısa süre tek bir büyük fikirle kapatır, sonra whip ile geri döner |
| "Vinyet / atmosfer" | Vignette + rim glow + film grain + zoom pulse — her zaman açık atmosfer katmanı |
| "Overlay'i sana bırakıyorum" | Agent script'i okur, görsel dili seçer; gerekince senden image asset (PNG / screenshot) ister |
| "Yoğun anlatım, az yazı" | Image-first — ekranda 3–5 kelime, geri kalanı motion |

## Instagram danger zones (1080×1920)

IG kendi UI'ını videonun üstüne bindirir. Anlamlı metni bu bölgelerden uzak tut.

```
x:0                                                      x:1080
 ┌──────────────────────────────────────────────────────┐ y:0
 │  ░░░  TOP UI — clock / profile row  (y 0–140)     ░░░  │
 ├──────────────────────────────────────────────────────┤ y:140
 │                                                        │
 │     ┌────────────────────────────────────────┐        │  ← .cap-upper (top:160)
 │     │                                         │   R    │
 │     │            SAFE TEXT BOX                │   I    │
 │     │   centered band  x[90,990]  (≤900 wide) │   G  ▓ │
 │     │   ── clears the right rail (x 960+) ──  │   H  ▓ │  RIGHT action rail
 │     │                                         │   T  ▓ │  like/comment/share/save
 │     │  .cap-mid (top:856) — split/empty mid   │      ▓ │  x 960–1080, y 1050–1700
 │     │                                         │   ▓  ▓ │
 │     │  .cap-seg1 (top:1200) under baked over. │   ▓    │
 │     │  .cap-lower (top:1330) chin must clear  │        │
 │     └────────────────────────────────────────┘        │
 │                                                        │
 ├──────────────────────────────────────────────────────┤ y:1560
 │  ░░  BOTTOM UI — caption · @user · audio · CTA  ░░     │
 └──────────────────────────────────────────────────────┘ y:1920
```

| Band | `top` | Ne zaman |
| --- | --- | --- |
| `.cap-upper` | 160 | **DEFAULT** for tight talking-head selfies — saç/alın/bg üstünde, gözlerin üstünde, top UI'dan uzak |
| `.cap-mid` | 856 | Sadece görsel split / boş orta zone varsa (özne bir kenara itilmiş). Ortalı yüz üstünde KULLANMA |
| `.cap-lower` | 1330 | Klasik lower-third — sadece çene/boyun temizse. ⚠️ yakın selfie'de 2 satır ağza taşabilir |
| `.cap-seg1` | 1200 | Baked top overlay (diagram/full-bg) frame'in üst ~%60'ını kaplıyorsa, onun hemen altı |

> Yatay: kullanılabilir `x[60,1010]`, ama centered band genişliği ≤900 tut →
> sağ action rail'e (x 960+) taşma. Base `.cap` = `left:90px` + `width:900px` →
> `x[90,990]`, sağ rail'i marjla geçer. Detay: `kit/captions.css`.

## How to use a theme

İki adım, başka hiçbir şey:

**1) Theme `<head>` bloğunu yapıştır** (font link'leri + `<style>`). Her theme
dosyasının başındaki yorum bloğu kopyalanacak EXACT satırları sırayla verir
(GSAP → Inter/Fontshare fallback → `@font-face`). Theme'in CSS'ini bir
`<style>` içine inline et (composition self-contained kalsın).

**2) Clip'leri kontrat class'larıyla yaz:**

```html
<!-- atmosphere layer, track 1, always on — .atmo-bot MUST be last (see below) -->
<div class="clip atmo-vig"   data-start="0" data-duration="18.36" data-track-index="1"></div>
<div class="clip atmo-rim"   data-start="0" data-duration="18.36" data-track-index="1"></div>
<div class="clip atmo-grain" data-start="0" data-duration="18.36" data-track-index="1"></div>
<div class="clip atmo-bot"   data-start="0" data-duration="18.36" data-track-index="1"></div>

<!-- big hook text, track 2 -->
<h1 class="clip cool glow-emerald" data-start="0.4" data-duration="2.0" data-track-index="2">
  CONSISTENCY<br>WINS
</h1>

<!-- caption, track 3, IG-safe band -->
<p class="clip cap cap-upper gsans" data-start="3.0" data-duration="2.4" data-track-index="3">
  her gün <b>tek</b> şey
</p>
```

`.cool` = hook/impact, `.gsans` = caption/body, `.cap-*` = güvenli band, glow =
neon read. **`nail.css` ↔ `fork-sunset.css` swap'ı her şeyi yeniden skinler** —
emerald+amber → coral+peach, Coolvetica/Product Sans → Cabinet Grotesk/General
Sans, atmosfer recolor — markup'a dokunmadan.

> ⚠️ **`.atmo-bot` ZORUNLU** — atmosfer katmanının SON child'ı olarak her
> composition'a koy. Renderer ara sıra VIDEO katmanının alt ~86px'ini düşürür
> (per-seek artifact; encode/keyframe/CSS scale ile çözülmez — hepsi denendi).
> `.atmo-bot` sinematik bottom-fade DIV'i bu siyah bandı maskeler, IG alt-UI
> zone'unda zaten oturur. Her iki tema da içerir.

## How to fork (başkasına vermek için)

Başkasıyla paylaşırken **`fork-sunset.css`** kullan (nail'in markası değil),
yapıyı aynı tut. Bu, "Sunset Editorial" — coral/peach üzeri warm paper,
Fontshare fontları (HTTP 200 doğrulandı). Class kontratı `nail.css` ile birebir
aynı olduğu için bütün composition'lar tek dosya değişimiyle tarafsız bir kimliğe
döner. Fork için niyet: kullanıcı yarı-hazır videosunu bırakır, bir agent
overlay'leri hazırlar. Bu akışı **`kit/AGENT.md`** sürer (agent-assisted console).

## Track-index convention

| Track | İçerik |
| --- | --- |
| 0 | video |
| 1 | atmosphere (vignette / rim / grain) |
| 2 | full-screen scenes & big text |
| 3 | captions |
| 4 | micro overlays / camera frame |
| 6 | pop sfx (from the user's own library) |
| 7 | whoosh / transition sfx |
| 8 | audio |

## HyperFrames key rules

- Her timed element: `data-start` + `data-duration` + `data-track-index`.
- Timing olan her element `class="clip"` taşımalı (framework görünürlüğü bununla yönetir).
- Timeline **paused** ve `window.__timelines["main"]` üzerinde kayıtlı:
  ```js
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = gsap.timeline({ paused: true });
  ```
- Video `muted` + ayrı `<audio>` element ses için.
- Sadece deterministik mantık — `Date.now()` / `Math.random()` / network YOK.

## SFX — "pıt" pops

Overlay/caption pop-in'lerinde hafif "pıt" sesi — **sadece kullanıcının KENDİ SFX
kütüphanesinden** (kitte sentetik ses yok). Yumuşak, düşük-geçişli (low-pass) bir
UI pop/tick seç, ses 14–20 dB altında; seçimi `sfx-map.json`'a yaz (bkz.
`kit/split-motion/SKILL.md` §SFX ve `kit/split-motion/sfx_mix.py`). **Pop'ları whoosh/transition SFX'ten AYRI bir track'e
koy** — pop'lar track 6, whoosh'lar track 7, ana ses track 8. ⚠️ hyperframes
aynı track'te çakışan clip'lerde HATA verir; pop+whoosh asla aynı track'te olmaz.

## Source video encoding

Source video **full-range** kodlanmalı — limited-range (`yuv420p` / tv) alt-band
drop'unu KÖTÜLEŞTİRİR. 1080×1920 render hedefine downscale + temiz seek için sık
keyframe:

```bash
ffmpeg -y -i INPUT \
  -vf "scale=1080:1920:flags=lanczos" \
  -c:v libx264 -profile:v high -pix_fmt yuvj420p -color_range pc \
  -r 30 -g 15 -keyint_min 15 -crf 19 -preset slow \
  -movflags +faststart -c:a aac -b:a 192k \
  assets/source.mp4
```

## Render

```bash
npm run check    # lint + validate + inspect — değişiklikten sonra HER ZAMAN çalıştır (0 error şart)
npm run render   # MP4'e render
```

> `npm run dev` uzun-ömürlü preview server'dır (bloklar). Claude Code'da
> `run_in_background: true` ile başlat — foreground'da timeout olur, server ölür.

## Style: split-motion (podcast → motion-panel reel)

`kit/split-motion/` — top motion panel (dot grid, glowing hero objects every 1.5–3 s,
recurring chapter device fly-ins) over a bottom speaker card, one-word seam captions on
every word, 4–5 full-screen punch-ins, recap ending. Start with `kit/split-motion/SKILL.md`;
worked example: `split-motion-dai/`.
