#!/usr/bin/env python3
"""Assemble index.html from src/template.html + kit/split-motion + data/*.json.

usage: python3 -I scripts/build.py
Deterministic: geometry is computed here (no Math.random at runtime).
"""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "split-motion")

tpl = open(os.path.join(ROOT, "src", "template.html")).read()
css = open(os.path.join(KIT, "split-motion.css")).read()
smk = open(os.path.join(KIT, "sm-anim.js")).read()
edl = json.load(open(os.path.join(ROOT, "data", "edl.json")))
words = json.load(open(os.path.join(ROOT, "data", "words.json")))
VT = edl["video_total"]

# ---------- captions -----------------------------------------------------------
HL = {"gratification": "hl", "now": "hl", "stop": "hl-r", "no": "hl-r", "ready": "hl-r",
      "preparation": "hl-g", "catalog": "hl", "dropping": "hl-g", "consistent": "hl-g",
      "opportunity": "hl", "fireworks": "hl", "wait": "hl", "contract": "hl", "lawyer": "hl-g",
      "zero": "hl-r", "a.": "hl-g", "level": "hl", "paper": "hl"}
# captions lead the sound by 2 frames: the word pop takes 0.1 s to scale in, so a
# caption that starts exactly on the acoustic onset reads as late.
LEAD = 2 / 30
caps = []
for i, w in enumerate(words):
    raw = w["w"]
    txt = raw.strip('"').rstrip('.,!?"').strip('"')
    key = raw.lower().strip('"').rstrip(',!?"')
    low = txt if txt in ("I", "A") else txt.lower()
    cls = HL.get(key.rstrip('.'), "")
    if raw == "A.":
        cls = "hl-g"
    if key == "now" and False:
        cls = ""
    caps.append(f'  <div class="clip sm-cap {cls}" id="w{i}" data-start="{max(0, w["t"] - LEAD):.3f}" '
                f'data-duration="{w["d"]:.3f}" data-track-index="3">{low}</div>')

# ---------- generated geometry --------------------------------------------------
def b4tiles():
    out = []
    for k in range(16):
        r, c = divmod(k, 4)
        g = "g" if k % 5 == 0 else "full"
        out.append(f'<div class="tile {g}" style="left:{c*95}px;top:{r*110}px;width:85px;height:100px"></div>')
    return "".join(out)


def b5days():
    out = []
    for k in range(28):
        r, c = divmod(k, 7)
        out.append(f'<div class="day" style="left:{c*108}px;top:{r*108}px"><div class="fill"></div>'
                   f'<svg viewBox="0 0 24 24"><path d="M4 12l5 5L20 6" fill="none" stroke="#002612" stroke-width="3.5" '
                   f'stroke-linecap="round" stroke-linejoin="round"/></svg></div>')
    return "".join(out)


def fireworks():
    cols = ["#ffc53d", "#ff3346", "#39ff8f", "#ffffff"]
    out = []
    for bi, (cx, cy, R, n) in enumerate([(500, 400, 330, 22), (790, 210, 190, 14), (220, 230, 190, 14)], 1):
        g = [f'<g class="b{bi}">']
        for k in range(n):
            a = 2 * math.pi * k / n + bi * .3
            r0, r1 = R * .16, R * (0.82 + 0.18 * ((k * 7) % 5) / 4)
            x0, y0 = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
            x1, y1 = cx + r1 * math.cos(a), cy + r1 * math.sin(a)
            col = cols[(k + bi) % 4]
            g.append(f'<path class="ray" pathLength="1" d="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}" stroke="{col}" '
                     f'stroke-width="{7 if bi == 1 else 5}" stroke-linecap="round" stroke-dasharray="1" stroke-dashoffset="1" '
                     f'style="filter:drop-shadow(0 0 8px {col})"/>')
        for k in range(n + 6):
            a = 2 * math.pi * (k + .5) / (n + 6)
            rr = R * (1.0 + 0.25 * ((k * 3) % 4) / 3)
            col = cols[k % 4]
            g.append(f'<circle class="pt" cx="{cx}" cy="{cy}" r="{7 if bi == 1 else 5}" fill="{col}" '
                     f'data-dx="{rr*math.cos(a):.1f}" data-dy="{rr*math.sin(a):.1f}" opacity="0" '
                     f'style="filter:drop-shadow(0 0 8px {col})"/>')
        g.append("</g>")
        out.append("".join(g))
    return "".join(out)


def ringdots():
    out = []
    for k in range(36):
        a = 2 * math.pi * k / 36
        r = 270
        col = "#ffc53d" if k % 3 == 0 else "rgba(255,255,255,.55)"
        out.append(f'<circle cx="{300+r*math.cos(a):.1f}" cy="{300+r*math.sin(a):.1f}" r="{7 if k%3==0 else 4}" fill="{col}"/>')
    return "".join(out)


def ringlights():
    out = []
    for k in range(10):
        a = 2 * math.pi * k / 10
        col = ["#39ff8f", "#ffc53d", "#ffffff"][k % 3]
        out.append(f'<circle cx="{300+210*math.cos(a):.1f}" cy="{300+210*math.sin(a):.1f}" r="9" fill="{col}" '
                   f'style="filter:drop-shadow(0 0 10px {col})"/>')
    return "".join(out)


def meter():
    out = []
    for k in range(8):
        h = 60 + k * 48
        col = "#ffc53d" if k < 5 else "#ff3346"
        out.append(f'<i style="height:{h}px;background:linear-gradient(180deg,{col},rgba(255,255,255,.08));box-shadow:0 0 18px {col}"></i>')
    return "".join(out)


def doclines():
    out = []
    widths = [400, 360, 420, 300, 380, 350, 410, 330, 420, 260]
    for k, w in enumerate(widths):
        y = 140 + k * 44
        out.append(f'<path class="sm-line dl" pathLength="1" d="M60 {y} H{60+w}" style="stroke-width:6;stroke:rgba(255,255,255,.8)"/>')
    return "".join(out)


html = tpl
html = html.replace("/*{{CSS}}*/", css).replace("/*{{SMKIT}}*/", smk)
html = html.replace("{{CAPTIONS}}", "\n".join(caps))
html = html.replace("{{VT}}", f"{VT:.3f}").replace("{{PUNCH}}", json.dumps(edl["punch"]))
for k, fn in {"B4TILES": b4tiles, "B5DAYS": b5days, "FIREWORKS": fireworks, "RINGDOTS": ringdots,
              "RINGLIGHTS": ringlights, "METER": meter, "DOCLINES": doclines}.items():
    html = html.replace("<!--{{%s}}-->" % k, fn())
assert "{{" not in html, re.findall(r"\{\{\w+\}\}", html)
open(os.path.join(ROOT, "index.html"), "w").write(html)
print("index.html", len(html), "bytes,", len(caps), "captions, VT", VT)
