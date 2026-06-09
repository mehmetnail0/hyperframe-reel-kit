# Build centered 1-2 word cinematic ASS captions from whisper.cpp word tokens.
import json, re

W, H = 3840, 2160
CX, CY = W // 2, H // 2

# ---------- 1. word stream from tokens ----------
d = json.load(open("transcript.json"))
words = []  # (text, t0, t1) in seconds
for seg in d["transcription"]:
    for tok in seg["tokens"]:
        t = tok["text"]
        if t.startswith("[_"):
            continue
        t0, t1 = tok["offsets"]["from"] / 1000, tok["offsets"]["to"] / 1000
        if t.startswith(" ") or not words:
            words.append([t.strip(), t0, t1])
        else:  # subword continuation
            words[-1][0] += t
            words[-1][2] = t1

# ---------- 2. corrections on the word stream ----------
# (pattern words) -> (replacement words); case-insensitive match on stripped text
RULES = [
    ("Şey anlamıyorum", "şeyi anlamıyorum"),
    ("o bu ya da stock'luğu satıyor", "o bu ya da stokluyor satıyor"),
    ("drop shipping,", "dropshipping,"),
    ("Mark'ın olması", "Markanın olması"),
    ("sonuçta et ticaret.", "sonuçta e-ticaret."),
    ("bu adamları?", "bu adamların?"),
    ("kazanıyorsan niye içerik üretiyorlar", "kazanıyorlarsa niye içerik üretiyorlar"),
    ("En garantiye adamları", "En garantici adamlar"),
    ("içeri küretmen", "içerik üretmen"),
    ("içeri küretirsin", "içerik üretirsin"),
    ("içeri kürettin", "içerik ürettin"),
    ("saplementinden dinenç lastiğini", "supplement'inden direnç lastiğine"),
    ("bir ticareta oluşturursun", "bir ticaret ağı oluşturursun"),
    ("istiyorsun dur.", "istiyorsundur."),
    ("Tişör satıyorsun dur,", "Tişört satıyorsundur,"),
    ("Kurcağın", "Kuracağın"),
    ("stock tutma", "stok tutma"),
    ("o çıktığıyla", "o çıktıyla"),
    ("informarketing'e", "info-marketing'e"),
    ("kafanı rahatı almak", "kafanı rahata almak"),
    ("stresiz", "stressiz"),
    ("yüzdeyiz garantisi", "yüzde yüz garantisi"),
    ("nişene odaklı", "nişine odaklı"),
    ("Uzmanlığın odaklı", "uzmanlığına odaklı"),
    ("En basitinden bir ticaretçinin", "En basitinden e-ticaretçinin"),
]

def norm(s):
    return re.sub(r"[.,!?;:]+$", "", s.strip()).lower()

i = 0
out = []
while i < len(words):
    matched = False
    for pat, rep in RULES:
        pw = pat.split()
        if i + len(pw) <= len(words) and all(
            norm(words[i + k][0]) == norm(pw[k]) for k in range(len(pw))
        ):
            rw = rep.split()
            t0 = words[i][1]
            t1 = words[i + len(pw) - 1][2]
            span = max(t1 - t0, 0.01)
            n = len(rw)
            for k, wtxt in enumerate(rw):
                a = t0 + span * k / n
                b = t0 + span * (k + 1) / n
                out.append([wtxt, a, b])
            i += len(pw)
            matched = True
            break
    if not matched:
        out.append(words[i])
        i += 1
words = out

# mark clause/sentence boundaries before stripping punctuation
for w in words:
    w.append(bool(re.search(r"[.,!?;:]$", w[0])))  # w[3] = boundary
    w[0] = re.sub(r"[.,!?;:]+$", "", w[0])
words = [w for w in words if w[0]]

# everything lowercase (Turkish-aware: İ→i, I→ı)
for w in words:
    w[0] = w[0].replace("İ", "i").replace("I", "ı").lower()

# ---------- 3. chunk into 1-2 word cues ----------
cues = []  # (text, t0, t1)
i = 0
while i < len(words):
    w = words[i]
    pair = None
    if i + 1 < len(words) and not w[3]:  # never pair across clause boundary
        nxt = words[i + 1]
        gap = nxt[1] - w[2]
        if gap < 0.35 and len(w[0]) + len(nxt[0]) + 1 <= 16:
            pair = nxt
    if pair:
        cues.append([w[0] + " " + pair[0], w[1], pair[2]])
        i += 2
    else:
        cues.append([w[0], w[1], w[2]])
        i += 1

# display window: hold until next cue starts, but never hang > +0.45s into silence
events = []
for k, (txt, t0, t1) in enumerate(cues):
    if k + 1 < len(cues):
        end = min(cues[k + 1][1], t1 + 0.45)
        end = max(end, t0 + 0.30)  # minimum readable
        end = min(end, cues[k + 1][1])  # never overlap next cue
    else:
        end = t1 + 0.6
    events.append((txt, t0, end))

# ---------- 4. emit ASS ----------
def ts(t):
    t = max(t, 0)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

FS = 138          # reference proportion, bright-scene adjusted
DRIFT = 16        # px drop-from-above (subtle)
header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cine,Google Sans Flex,{FS},&H00FFFFFF,&H00FFFFFF,&HCC000000,&H00000000,0,0,0,0,100,100,1,0,1,5,0,5,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = [header]
for txt, t0, t1 in events:
    # pat-pat: instant on/off, no move, soft even halo at low opacity
    ov = f"{{\\an5\\pos({CX},{CY})\\blur9}}"
    lines.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},Cine,,0,0,0,,{ov}{txt}\n")

open("subs.ass", "w", encoding="utf-8").write("".join(lines))
print(f"{len(events)} cues written")
for txt, t0, t1 in events[:12]:
    print(f"  {t0:6.2f}-{t1:6.2f}  {txt}")
