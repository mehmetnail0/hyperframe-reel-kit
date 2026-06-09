# Emit 5 ASS variants (shadow treatments) time-shifted for a sample window.
import re

T0, T1 = 89.0, 92.4  # sample window in source seconds

src = open("subs.ass").read()
head, ev = src.split("[Events]")
ev_lines = [l for l in ev.strip().splitlines() if l.startswith("Dialogue:")]

def parse_ts(s):
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)

def fmt_ts(t):
    t = max(t, 0)
    return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"

# variant: (name, outline, outline_alpha_hex, shadow, back_alpha_hex, blur)
VARIANTS = [
    ("s1-yok",        0, "00", 0,   "00", 0.8),   # no shadow at all
    ("s2-fisilti",    3, "D8", 0,   "00", 7),     # 15% wide whisper halo
    ("s3-genis-soluk",5, "CC", 0,   "00", 9),     # 20% wider, ultra faint
    ("s4-mini-offset",0, "00", 2,   "C8", 2.5),   # tiny 22% drop shadow only
    ("s5-v3-hafif",   7, "BE", 0,   "00", 6),     # v3 shape but 25% opacity
]

for name, outl, oa, shad, ba, blur in VARIANTS:
    style = (f"Style: Cine,Google Sans Flex,138,&H00FFFFFF,&H00FFFFFF,"
             f"&H{oa}000000,&H{ba}000000,0,0,0,0,100,100,1,0,1,{outl},{shad},5,60,60,60,1")
    h = re.sub(r"Style: Cine.*", style, head)
    out = [h + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"]
    for l in ev_lines:
        parts = l.split(",", 3)
        s, e = parse_ts(parts[1]), parse_ts(parts[2])
        if e <= T0 or s >= T1:
            continue
        text = l.split(",", 9)[9]
        text = re.sub(r"\\blur[\d.]+", f"\\\\blur{blur}", text)
        out.append(f"Dialogue: 0,{fmt_ts(s-T0)},{fmt_ts(e-T0)},Cine,,0,0,0,,{text}\n")
    open(f"sample_{name}.ass", "w").write("".join(out))
    print(name, "ok")
