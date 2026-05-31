<div align="center">

# 🎬 HyperFrame Reel Studio

**Konuşma videonu sürükle bırak → cilalı bir dikey reel çıksın.**
Altyazı, hareket ve atmosferi Claude Code yazıyor — sen sadece konuşuyorsun.

`Kod yok` · `Video editörü yok` · `Premiere eklentisi yok` · `Altyazıyı elle yazmak yok`

</div>

---

## Bu repo ne yapıyor?

Hazıra yakın bir **konuşma videon** var. Bu repo + **Claude Code**, onu Instagram'a hazır
bir reel'e çeviriyor:

- 🗣️ **Altyazıyı sen yazmıyorsun** — videodaki konuşmayı otomatik çıkarır (whisper),
  temizler, 3–5 kelimelik akıcı parçalara böler ve **tam konuştuğun ana** hizalar.
- 🎯 **Altyazıyı doğru yere koyar** — yüzünü, ağzını, ürünü/ekranı kapatmaz; boş ölü
  alana, IG'nin güvenli bölgelerine yerleştirir (kareleri tek tek ölçerek).
- ✨ **Cilalar** — marka teması, ince zoom darbeleri, atmosfer/vinyet, seyrek ses efektleri.
- 🔁 **"Deneme reels" için yeniden üretim** — tutan bir reel'ini tekrar attığında Instagram
  çoğu zaman "bunu zaten gördüm" deyip izlettirmez. Bu araç videoyu (altyazı + hareket +
  atmosfer + yeniden encode ile) algoritmanın *birebir aynı video* diye yakalaması
  zorlaşacak kadar değiştirir. **%100 garanti değil**, ama tutan içeriğini birkaç tur daha
  denemek için pratik bir yol.

> Altyapı: **HyperFrames CLI** (`npx hyperframes`) — HTML + CSS + GSAP ile render. Remotion değil.

---

## ⚡ Kurulum (tek seferlik)

| # | Adım | Nasıl |
|---|------|-------|
| 1 | **Claude Code'u indir** | https://claude.com/claude-code |
| 2 | **ffmpeg kur** | macOS `brew install ffmpeg` · Windows `winget install Gyan.FFmpeg` · Linux `sudo apt install ffmpeg` |
| 3 | **Repoyu al** | Bir klasör aç, Claude Code'u içinde başlat ve şunu yaz: <br> *"Şu repoyu buraya kur: `https://github.com/mehmetnail0/hyperframe-reel-kit.git`"* |

Claude Code repo klasöründe açılınca **`CLAUDE.md`'yi otomatik okur** — ne yapacağını bilir.
Başka kurulum yok; `node` ve `hyperframes` gerektiğinde kendiliğinden iner.

---

## 🎥 Reel üretmek (3 adım)

```
1.  Videonu pencereye sürükle (ya da dosya yolunu yapıştır)
2.  Düz Türkçe söyle ne istediğini
3.  Bekle → çıktı:  <reel-klasörün>/renders/*.mp4
```

Ajan arka planda: videoyu inceler → yüz/ürün için **güvenli bölgeleri ölçer** →
konuşmayı çıkarıp temizler → altyazı + hareketleri kurar → kalite kontrol (`npm run check`)
→ render eder → IG boyutuna (1080×1920) crop'lar.

> 💡 Emin olamadığı bir şey olursa **sana sorar** (belirsiz cümle, öne çıkarmak istediğin
> görsel vb.). Tahmin etmez.

---

## 💬 Örnek prompt'lar

Claude Code'a böyle yazabilirsin:

**Sıfırdan reel:**
> *"Bu videodan IG reel yap. Altyazıyı yüzümü kapatmayacak şekilde merkez-altta tut,
> sade ve şık olsun."*

**Tutan reel'i 'deneme' için yeniden üret:**
> *"Bu reel daha önce tuttu, tekrar atacağım. Altyazı + hafif hareket + atmosfer ekleyip
> yeniden encode ederek Instagram'ın 'aynı video' diye görmesini zorlaştır."*

**Konuşmayı otomatik altyazıla:**
> *"Videodaki konuşmayı sen çıkar, temizle ve altyazı yap — emin olamadığın 1-2 kelimeyi
> bana sor."*

**Render'ı gördükten sonra ince ayar:**
> *"Altyazı biraz yukarıda, bir tık aşağı al."*
> *"Zoom'lar fazla, azalt — daha sakin olsun."*
> *"Şu kelimeyi sarı yapıp vurgula."*
> *"Bir alternatif daha üret, daha agresif SFX'li."*

---

## 🎨 Temalar (drop-in, değiştirilebilir)

Tek tema dosyasını değiştirince **tüm reel yeniden boyanır** (ikisi de aynı sınıf
sözleşmesini kullanır):

- **`kit/themes/fork-sunset.css`** — herkese açık varsayılan kimlik (coral/peach + temiz font).
  *"fork-sunset temasıyla üret"* de, yeter.
- **`kit/themes/nail.css`** — repo sahibinin markası (emerald + amber, Türkçe-uyumlu font).

**Kendi markan için:** `kit/themes/` altına bir tema kopyala, renk token'larını + fontları
değiştir, "şu temayla üret" de.

---

## 🗂️ Ne nerede

| Yol | Ne işe yarar |
|---|---|
| **`CLAUDE.md`** | Ajanın beyni — açılışta okur; tüm akış + kurallar burada |
| **`kit/`** | Tasarım sistemi (tek dosya değiştir → tüm reel re-skin) |
| `kit/themes/` | `nail.css` + `fork-sunset.css` |
| `kit/captions.css` | IG güvenli-bölge altyazı bantları |
| `kit/components.html` | Çizimsel/vektörel SVG parçaları |
| `kit/anim.js` | GSAP yardımcıları (`window.HFKit`) |
| `kit/AGENT.md` | Ajan için detaylı çalışma talimatı + render checklist |
| `kit/README.md` | Yetenek menüsü + IG danger-zone haritası |

> Örnek reel klasörleri (sahibin kişisel videoları + lisanslı ses kütüphanesi) gizlilik
> için repoya dahil değildir. Sen kendi videonu eklediğinde ajan yapıyı sıfırdan kurar.

---

## 🛠️ Gereksinimler & komutlar

**Gerekir:** Claude Code · Node.js (`npx hyperframes` otomatik iner) · ffmpeg
**Opsiyonel:** whisper.cpp — otomatik altyazı için (`brew install whisper-cpp`)

```bash
npm run dev      # canlı önizleme (uzun süren — arka planda)
npm run check    # lint + validate + inspect  (0 hata olmalı)
npm run render   # MP4 render → renders/   (yüksek kalite + fps için: -- --fps 50 --quality high)
npm run publish  # paylaşılabilir link
```

<div align="center">

---

*Videonu ver, gerisini konuşarak hallet.*

</div>
