# HyperFrame Reel Studio

Hazıra yakın bir **konuşma videonu** ver → ajan sana captions + çizimsel hareketler +
atmosferle cilalı bir **dikey reel** çıkarsın. Kod yazmana gerek yok; ajan neye ihtiyacı
varsa senden ister.

Altyapı: **HyperFrames CLI** (`npx hyperframes@0.6.49`) — HTML + CSS + GSAP. Remotion değil.

---

## Nasıl kullanılır (3 adım)

1. **Bu repoyu al.** Claude Code'da GitHub linkini yapıştır (veya `git clone`), sonra repo
   klasöründe Claude Code'u aç. Ajan açılışta `CLAUDE.md`'yi okur ve ne yapacağını bilir.
2. **Videonu sürükle** (veya yolunu ver) ve ne anlattığını söyle. Örnek:
   > "Bu videoyu reel yap — konu: içerik üretiminde istikrar. Instagram Reels için.
   >  Marka temam (nail) olsun, altyazıları güvenli bölgelere koy."
3. **Bekle.** Ajan: videoyu inceler → güvenli bölgeleri ölçer → metni çıkarır/temizler →
   altyazıları + çizimsel overlay'leri kurar → `npm run check` (0 hata) → render eder.
   Çıktı: `<senin-reel>/renders/*.mp4`.

**Ajan senden şunları isteyebilir:** doğru altyazı metni (belirsiz cümlelerde), öne çıkacak
görseller (PNG/screenshot/logo), hangi overlay'leri sen koydun / hangilerini ona bırakıyorsun.

---

## Ne nerede (klasör haritası)

| Klasör | Ne işe yarar |
|---|---|
| **`CLAUDE.md`** | Ajanın beyni — açılışta okur, tüm akış + kurallar burada |
| **`kit/`** | **Tasarım sistemi.** Tek tema dosyası değiştir → tüm reel re-skin |
| `kit/themes/nail.css` | Senin markan (emerald + amber, Coolvetica + Plus Jakarta) |
| `kit/themes/fork-sunset.css` | Paylaşım kimliği (coral/peach) — **senin renklerin değil** |
| `kit/captions.css` | IG güvenli-bölge altyazı bantları (`.cap-upper`, `.cap-seg1`…) |
| `kit/components.html` | Çizimsel/vektörel SVG parçaları (streak, scroll ok, growth, X, badge, full-bg punch) |
| `kit/anim.js` | GSAP yardımcıları (`window.HFKit`) |
| `kit/assets/sfx/` | "pıt" pop sesleri (`pop.wav`, `pop_hi.wav`) |
| `kit/README.md` | **Yetenek menüsü** ("sana çıkaracağım iş tipleri") + IG danger-zone haritası |
| `kit/AGENT.md` | Ajan için detaylı çalışma talimatı (render checklist) |
| **`personal-brand-reel/`** | **Örnek reel** (18sn). Yeni reel için yapısını kopyala |
| `nail-ai-reel/`, `nwn-incele-reel/` | Eski örnek reel'ler |
| `references/` | Referans videolar/kareler |

---

## Temalar

İki tema da aynı sınıf sözleşmesini kullanır (`.cool` `.gsans` `.atmo-*` + glow), yani tek
tema bloğunu değiştirince her şey yeniden boyanır:
- **nail** — repo sahibi (nailingai.co markası).
- **fork-sunset** — başkalarıyla paylaşırken (ayrı kimlik, farklı font + renkler).

Forklayıp kendi markanı yapmak için: `kit/themes/` altına yeni bir tema dosyası ekle (mevcut
birini kopyala, token'ları + fontları değiştir) ve onu kullan.

---

## Gereksinimler

- **Claude Code** (bu repoyu açıp ajanı çalıştırmak için)
- **Node.js** (`npx hyperframes@0.6.49` otomatik iner)
- **ffmpeg** (kaynak videoyu encode etmek + kareleri incelemek için)

## Komutlar (her reel klasöründe)

```bash
npm run dev      # canlı önizleme sunucusu (uzun süren — arka planda çalıştır)
npm run check    # lint + validate + inspect (0 hata olmalı)
npm run render   # MP4 render -> renders/
npm run publish  # paylaşılabilir link
```
