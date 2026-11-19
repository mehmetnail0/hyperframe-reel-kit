#!/usr/bin/env python3
"""Scene compiler: plan.json (+ cut words) -> HyperFrames index.html (and render chunks).

    from scenes import compile_reel
    html = compile_reel(plan, words, total, ctx)            # full composition (preview / check)
    html = compile_reel(plan, words, total, ctx, chunk=(off, dur))   # one render chunk

Every scene type in vocab.json has a generator here: gen_<type>(sid, spec, t0, t1, R) -> (html, js)
R = seeded random (deterministic per reel+beat), so the same plan always renders the same frames
while two reels never look alike. JS only calls KW.* verbs (runtime/kw.js) on `tl`.
Text markup in plan strings: *serif italic*  [red box]  _underline_
"""
import html as H
import json, math, os, random, re

HERE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.join(HERE, "runtime")
PANEL_H = 1370
FPS = 30


def esc(s):
    return H.escape(str(s), quote=True)


def mark(s):
    s = esc(s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"\[(.+?)\]", r'<span class="box">\1</span>', s)
    s = re.sub(r"_(.+?)_", r'<span class="ul">\1</span>', s)
    return s


def words_markup(s):
    """header: wrap words (keeping markup groups whole) in .w spans for word-by-word typing."""
    out, i = [], 0
    toks = re.findall(r"\*[^*]+\*|\[[^\]]+\]|_[^_]+_|\S+|\n", s)
    for t in toks:
        out.append("<br>" if t == "\n" else f'<span class="w">{mark(t)}</span>')
    return " ".join(out).replace(" <br> ", "<br>")


def stagger(t0, t1, n, start=.25, span=.6):
    if n <= 0:
        return []
    a = t0 + start
    b = max(a + .2, t0 + (t1 - t0) * span)
    step = min(.55, (b - a) / max(1, n - 1)) if n > 1 else 0
    return [round(a + k * step, 3) for k in range(n)]


def item_times(spec, t0, t1, n, wt):
    """sub-event times: explicit word indices (spec['at'] list) when given, else staggered."""
    at = spec.get("at") or []
    ts = []
    for k in range(n):
        if k < len(at) and at[k] is not None and wt(at[k]) is not None and t0 <= wt(at[k]) < t1:
            ts.append(round(wt(at[k]) - .05, 3))
        else:
            ts.append(None)
    fill = stagger(t0, t1, n)
    out = [ts[k] if ts[k] is not None else fill[k] for k in range(n)]
    last = max(t0 + .2, t1 - .6)  # every item visible for >= 0.6 s, in order
    for k in range(n):
        lo = (out[k - 1] + .15) if k else t0 + .15
        out[k] = round(min(max(out[k], lo), last), 3)
    return out


SKY = [("#ff6b6b", "#5f27cd"), ("#feca57", "#ff6b6b"), ("#48dbfb", "#0abde3"), ("#1dd1a1", "#10ac84"), ("#a29bfe", "#6c5ce7"),
       ("#fd79a8", "#e84393"), ("#fab1a0", "#e17055"), ("#81ecec", "#00cec9"), ("#ffeaa7", "#fdcb6e"), ("#74b9ff", "#0984e3"),
       ("#2d3436", "#636e72"), ("#dfe6e9", "#b2bec3")]


def thumb(x, y, w, h, R, label=None, cls=""):
    a, b = R.choice(SKY)
    ang = R.choice([120, 135, 160, 200])
    inner = f'<div class="sky" style="background:linear-gradient({ang}deg,{a},{b})"></div>'
    kind = R.random()
    if kind < .4:
        inner += '<div class="who"></div>'
    elif kind < .7:
        inner += '<div class="play"></div>'
    else:
        inner += "".join(f'<div class="ln" style="top:{20 + k * 14}%;width:{R.choice([50, 62, 74, 80])}%"></div>' for k in range(3))
    if label:
        inner += (f'<div style="position:absolute;left:0;right:0;bottom:8%;text-align:center;font-weight:900;font-size:{max(18, int(w / 7))}px;'
                  f'color:#fff;text-shadow:0 2px 8px rgba(0,0,0,.8);letter-spacing:-.02em">{mark(label)}</div>')
    return f'<div class="thumb {cls}" style="left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;height:{h:.0f}px">{inner}</div>'


ICONS = {  # 24x24 stroke icons (hand-made, MIT-free)
    "bulb": "M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.8.8 1.3 1.8 1.4 2.9h5.2c.1-1.1.6-2.1 1.4-2.9A6 6 0 0 0 12 3z",
    "target": "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M12 7a5 5 0 1 0 0 10a5 5 0 1 0 0-10M12 11a1 1 0 1 0 0 2a1 1 0 1 0 0-2",
    "rocket": "M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2M9 12l3 3M14 4c3-1 6-1 6-1s0 3-1 6l-6 6-5-5 6-6zM15 9a1 1 0 1 0 0 .1",
    "clock": "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M12 7v5l3 2",
    "money": "M3 6h18v12H3zM12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6M6 9v.01M18 15v.01",
    "chart": "M4 20V4M4 20h16M8 16l4-5 3 3 5-7",
    "warning": "M12 3l10 18H2L12 3zM12 10v4M12 17v.5",
    "check": "M4 12.5l5 5L20 6.5",
    "cross": "M5 5l14 14M19 5L5 19",
    "megaphone": "M3 10v4h4l8 5V5L7 10H3zM18 9c1.5 1 1.5 5 0 6",
    "eye": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6",
    "heart": "M12 20s-8-5-8-11a4.5 4.5 0 0 1 8-2.5A4.5 4.5 0 0 1 20 9c0 6-8 11-8 11z",
    "user": "M12 4a4 4 0 1 0 0 8a4 4 0 1 0 0-8M4 21c0-4 4-6 8-6s8 2 8 6",
    "users": "M9 5a3.5 3.5 0 1 0 0 7a3.5 3.5 0 1 0 0-7M2 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5M16 5.5a3 3 0 0 1 0 6M18 14.5c2.5.5 4 2.3 4 5",
    "play": "M7 4l13 8-13 8V4z",
    "camera": "M3 7h4l2-3h6l2 3h4v13H3zM12 10a3.5 3.5 0 1 0 0 7a3.5 3.5 0 1 0 0-7",
    "mic": "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3",
    "calendar": "M4 6h16v15H4zM4 10h16M8 3v5M16 3v5",
    "lock": "M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4",
    "key": "M8 15a4 4 0 1 0 0-.1M11 12l9-9M17 6l3 3",
    "fire": "M12 3s5 4 5 10a5 5 0 0 1-10 0c0-3 2-5 2-5s0 3 2 4c0-4 1-7 1-9z",
    "star": "M12 3l2.8 5.9 6.2.9-4.5 4.4 1 6.3L12 17.6 6.5 20.5l1-6.3L3 9.8l6.2-.9z",
    "trophy": "M7 4h10v5a5 5 0 0 1-10 0V4zM7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4M12 14v4M8 21h8M9 18h6",
    "brain": "M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 3 3h1V4zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-3 3h-1V4z",
    "doc": "M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h7",
    "search": "M10 4a6 6 0 1 0 0 12a6 6 0 1 0 0-12M15 15l6 6",
    "chat": "M4 5h16v11H9l-5 4V5z",
    "gift": "M3 9h18v4H3zM5 13h14v8H5zM12 9v12M12 9s-1-5-4-5-2 5 4 5zM12 9s1-5 4-5 2 5-4 5z",
    "hourglass": "M6 3h12M6 21h12M7 3c0 5 10 6 10 9s-10 4-10 9M17 3c0 5-10 6-10 9s10 4 10 9",
    "mountain": "M2 20l7-12 4 6 3-4 6 10H2z",
}


def icon_svg(name, color="#fff", sw=1.6, cls="ln-draw"):
    d = ICONS.get(name, ICONS["star"])
    return (f'<svg viewBox="0 0 24 24"><path class="{cls}" pathLength="1" stroke-dasharray="1" d="{d}" '
            f'stroke="{color}" stroke-width="{sw}"/></svg>')


# ----------------------------------------------------------------------------- generators
def gen_orbit(sid, sp, t0, t1, R, wt):
    items = (sp.get("items") or ["idea", "format", "hook", "story", "edit"])[:6]
    n = len(items)
    cx, cy, rad = 540, 430, R.choice([300, 320, 340])
    rot0 = R.uniform(-.4, .4)
    tw, th = R.choice([(150, 200), (140, 210), (170, 190)])
    h = [f'<svg class="abs" style="left:0;top:0" width="1080" height="880"><circle class="dash" cx="{cx}" cy="{cy}" r="{rad}"/></svg>']
    js = []
    ts = item_times(sp, t0, t1, n, wt)
    for k, it in enumerate(items):
        a = rot0 + 2 * math.pi * k / n - math.pi / 2
        x, y = cx + rad * math.cos(a) - tw / 2, cy + rad * math.sin(a) - th / 2
        h.append(thumb(x, y, tw, th, R, it, cls=f"{sid}_t{k}"))
        js.append(f"KW.enter(tl,'#{sid} .{sid}_t{k}','pop',{ts[k]});")
    lab = sp.get("center") or sp.get("label") or ""
    h.append(f'<div class="pill red {sid}_c" style="left:540px;top:{cy}px;transform:translate(-50%,-50%);font-size:44px">{mark(lab)}</div>')
    js.insert(0, f"KW.enter(tl,'#{sid} .{sid}_c','pop',{t0 + .1:.3f});")
    if sp.get("hero"):  # continuous motion is a hero privilege
        js.append(f"tl.fromTo('#{sid} svg circle',{{rotation:0,transformOrigin:'{cx}px {cy}px'}},{{rotation:{R.choice([-12, 12])},duration:{t1 - t0:.2f},ease:'sine.inOut',immediateRender:false}},{t0:.3f});")
    return "".join(h), js, [("glow", t0 + .1)] + [("counter", t) for t in ts[:3]]


HL = ["var(--hl1)", "var(--hl2)", "var(--hl3)", "var(--hl4)", "var(--hl5)", "var(--red)"]


def gen_doc(sid, sp, t0, t1, R, wt):
    rows = (sp.get("rows") or ["Hook", "Body", "CTA"])[:6]
    W, Hh = 600, 760
    x0, y0 = 240, 40
    title = sp.get("title") or "Video Script"
    h = [f'<div class="card" style="left:{x0}px;top:{y0}px;width:{W}px;height:{Hh}px;border-color:rgba(255,255,255,.55)">'
         f'<div class="serif" style="position:absolute;left:0;right:0;top:26px;text-align:center;font-size:46px">{mark(title)}</div>']
    js = []
    ts = item_times(sp, t0, t1, len(rows), wt)
    cols = R.sample(HL[:5], 5)
    yy = 120
    for k, r in enumerate(rows):
        lab = r if isinstance(r, str) else r.get("label", "")
        c = cols[k % 5]
        nlines = R.choice([2, 2, 3])
        h.append(f'<div class="{sid}_r{k}" style="position:absolute;left:36px;top:{yy}px;width:{W - 72}px">'
                 f'<div style="display:flex;gap:12px;align-items:center;font-weight:700;font-size:28px">'
                 f'<span style="width:22px;height:22px;border-radius:4px;background:{c}"></span>{mark(lab)}</div>')
        for j in range(nlines):
            h.append(f'<div class="hlbar {sid}_b{k}" style="position:relative;margin-top:12px;width:{R.choice([88, 76, 94, 64])}%;background:{c};opacity:.9"></div>')
        h.append("</div>")
        js.append(f"KW.enter(tl,'#{sid} .{sid}_r{k}','rise',{ts[k]},.3);KW.grow(tl,'#{sid} .{sid}_b{k}',{ts[k] + .08:.3f},.4);")
        yy += 46 + nlines * 34 + 24
    for j in range(max(0, int((Hh - yy - 30) / 30))):
        h.append(f'<div style="position:absolute;left:36px;top:{yy + j * 30}px;width:{R.choice([80, 70, 90])}%;height:10px;border-radius:5px;background:rgba(255,255,255,.18)"></div>')
    h.append("</div>")
    return "".join(h), js, [("draw", t) for t in ts]


def gen_list(sid, sp, t0, t1, R, wt):
    items = (sp.get("items") or ["one", "two", "three"])[:6]
    n = len(items)
    W = R.choice([760, 800, 840])
    gap = 112 if n > 4 else 128
    y0 = max(20, (860 - n * gap) // 2)
    ts = item_times(sp, t0, t1, n, wt)
    h, js = [], []
    for k, it in enumerate(items):
        h.append(f'<div class="row {sid}_r{k}" style="left:{(1080 - W) // 2}px;top:{y0 + k * gap}px;width:{W}px">'
                 f'<div class="n">{k + 1:02d}</div><div class="t" style="color:rgba(255,255,255,0);text-shadow:0 0 14px rgba(255,255,255,.55)">{mark(it)}</div></div>')
        js.append(f"KW.unghost(tl,'#{sid} .{sid}_r{k} .t',{ts[k]});KW.light(tl,'#{sid} .{sid}_r{k}',{ts[k]},true);"
                  + (f"KW.light(tl,'#{sid} .{sid}_r{k}',{ts[k + 1]},false);" if k + 1 < n else ""))
    js.insert(0, f"tl.fromTo('#{sid} .row',{{autoAlpha:0,y:18}},{{autoAlpha:1,y:0,duration:.55,stagger:.07,ease:'back.out(1.15)',immediateRender:false}},{t0 + .05:.3f});")
    return "".join(h), js, [("counter", t) for t in ts]


def gen_phone(sid, sp, t0, t1, R, wt):
    head = sp.get("headline") or "6 Words"
    sub = sp.get("sub") or ""
    rows = (sp.get("rows") or [])[:4]
    x, y, w, hh = 300, 10, 480, 860
    sf = (sp.get("_screen_fit") or 1)
    h = [f'<div class="card {sid}_ph" style="left:{x}px;top:{y}px;width:{w}px;height:{hh}px;border-radius:64px;border:5px solid rgba(255,255,255,.85);background:#0d0d10;overflow:hidden">'
         f'<div class="screen" data-device="{sid}" style="position:absolute;inset:14px;border-radius:50px;overflow:hidden;background:#0b0b0f">'
         f'<div class="scr-in" style="position:absolute;inset:0;transform:scale({sf});transform-origin:50% 0">'
         f'<div style="position:absolute;left:156px;top:6px;width:130px;height:34px;border-radius:20px;background:#000"></div>'
         f'<div style="position:absolute;left:20px;right:20px;top:100px;text-align:center;font-weight:900;font-size:60px;color:var(--red2);letter-spacing:-.03em;line-height:1">{mark(head)}</div>'
         f'<div style="position:absolute;left:20px;right:20px;top:182px;text-align:center;font-size:32px;font-weight:700">{mark(sub)}</div>']
    ts = item_times(sp, t0, t1, len(rows), wt)
    js = []
    for k, r in enumerate(rows):
        h.append(f'<div class="{sid}_c{k}" style="position:absolute;left:0;right:0;top:{286 + k * 96}px;text-align:center">'
                 f'<span class="chip" style="position:relative;display:inline-block;max-width:380px;overflow:hidden;text-overflow:ellipsis;font-size:28px">{mark(r)}</span></div>')
        js.append(f"KW.enter(tl,'#{sid} .{sid}_c{k}','pop',{ts[k]});")
    for j in range(6):
        h.append(f'<div style="position:absolute;left:{26 + (j % 2) * 200}px;top:{286 + len(rows) * 96 + (j // 2) * 146}px;width:186px;height:132px;border-radius:14px;'
                 f'background:linear-gradient(135deg,{R.choice(SKY)[0]},{R.choice(SKY)[1]});opacity:.35"></div>')
    h.append("</div></div></div>")
    return "".join(h), js, [("tick", t) for t in ts[:2]]


def gen_grid(sid, sp, t0, t1, R, wt):
    n = int(sp.get("n") or R.choice([6, 8, 9, 12]))
    cols = 3 if n in (6, 9) else 4
    rows = math.ceil(n / cols)
    tw = 230 if cols == 3 else 190
    th = int(tw * 1.42)
    gx, gy = 22, 22
    W, Hh = cols * tw + (cols - 1) * gx, rows * th + (rows - 1) * gy
    sc = min(1, 840 / Hh)
    hi = int(sp.get("highlight", R.randrange(n)))
    h = [f'<div class="abs" style="left:{(1080 - W * sc) / 2:.0f}px;top:{(860 - Hh * sc) / 2:.0f}px;width:{W}px;height:{Hh}px;transform:scale({sc:.3f});transform-origin:0 0">']
    for k in range(n):
        r, c = divmod(k, cols)
        h.append(thumb(c * (tw + gx), r * (th + gy), tw, th, R, cls=f"{sid}_g{k}"))
    h.append("</div>")
    order = list(range(n))
    R.shuffle(order)
    js = [f"tl.fromTo('#{sid} .thumb',{{autoAlpha:0,scale:.92,y:10}},{{autoAlpha:1,scale:1,y:0,duration:.6,ease:'back.out(1.15)',stagger:{{each:.06,from:'{R.choice(['start', 'center', 'edges', 'random'])}'}},immediateRender:false}},{t0 + .05:.3f});"]
    th_t = round(t0 + min(1.6, (t1 - t0) * .55), 3)
    js.append(f"tl.to('#{sid} .{sid}_g{hi}',{{scale:1.12,zIndex:5,boxShadow:'0 0 0 6px #e8283c,0 0 60px rgba(232,40,60,.6)',duration:.3,ease:'power2.out'}},{th_t});")
    js.append(f"tl.to('#{sid} .thumb:not(.{sid}_g{hi})',{{opacity:.35,duration:.3}},{th_t});")
    if sp.get("label"):
        h.append(f'<div class="chip red {sid}_l" style="left:50%;top:800px;transform:translateX(-50%)">{mark(sp["label"])}</div>')
        js.append(f"KW.enter(tl,'#{sid} .{sid}_l','pop',{th_t + .1:.3f});")
    return "".join(h), js, [("swap", t0 + .05), ("glow", th_t)]


def gen_tree(sid, sp, t0, t1, R, wt):
    root = sp.get("root") or "Level 1"
    kids = (sp.get("children") or ["01", "02"])[:4]
    n = len(kids)
    rx, ry = 120, 430
    xs = 560
    ys = [430 + (k - (n - 1) / 2) * 170 for k in range(n)]
    ts = item_times(sp, t0, t1, n, wt)
    h = [f'<div class="pill red {sid}_root" style="left:{rx}px;top:{ry}px;transform:translateY(-50%);font-size:42px">{mark(root)}</div>',
         '<svg class="abs" style="left:0;top:0" width="1080" height="880">']
    js = [f"KW.enter(tl,'#{sid} .{sid}_root','slideR',{t0 + .05:.3f});"]
    for k, y in enumerate(ys):
        h.append(f'<path class="ln-draw {sid}_p{k}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" d="M{rx + 300} {ry} C {rx + 380} {ry}, {xs - 120} {y}, {xs} {y}" stroke="rgba(255,255,255,.8)" stroke-width="4"/>')
    h.append("</svg>")
    for k, (y, kid) in enumerate(zip(ys, kids)):
        h.append(f'<div class="row {sid}_k{k}" style="left:{xs}px;top:{y - 46:.0f}px;width:440px;font-size:36px"><div class="n">{k + 1:02d}</div><div class="t">{mark(kid)}</div></div>')
        js.append(f"KW.draw(tl,'#{sid} .{sid}_p{k}',{ts[k] - .2:.3f},.35);KW.enter(tl,'#{sid} .{sid}_k{k}','slideL',{ts[k]});")
    return "".join(h), js, [("draw", ts[0] - .2)] + [("tick", t) for t in ts[1:]]


def gen_radar(sid, sp, t0, t1, R, wt):
    n = int(sp.get("n") or R.choice([6, 8, 10, 12]))
    cx, cy = 540, 430
    h = [f'<svg class="abs" style="left:0;top:0" width="1080" height="880">']
    for k, r in enumerate([110, 200, 290, 380]):
        h.append(f'<circle class="{sid}_ring" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(255,255,255,{.75 - k * .12:.2f})" stroke-width="{5 - k}"/>')
    dots = []
    for k in range(n):
        a = R.uniform(0, 2 * math.pi)
        r = R.choice([110, 200, 290, 380])
        dots.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        h.append(f'<circle class="{sid}_d{k}" cx="{dots[-1][0]:.0f}" cy="{dots[-1][1]:.0f}" r="16" fill="#e8283c" style="filter:drop-shadow(0 0 10px #e8283c)"/>')
    h.append("</svg>")
    lab = sp.get("label") or ""
    if lab:
        h.append(f'<div class="pill {sid}_lab" style="left:{cx}px;top:{cy}px;transform:translate(-50%,-50%);font-size:36px">{mark(lab)}</div>')
    js = [f"tl.fromTo('#{sid} .{sid}_ring',{{scale:0,transformOrigin:'{cx}px {cy}px'}},{{scale:1,duration:.5,stagger:.08,ease:'expo.out',immediateRender:false}},{t0:.3f});"]
    ts = stagger(t0, t1, n, .45, .7)
    for k in range(n):
        js.append(f"tl.fromTo('#{sid} .{sid}_d{k}',{{scale:0,transformOrigin:'{dots[k][0]:.0f}px {dots[k][1]:.0f}px'}},{{scale:1,duration:.25,ease:'back.out(3)',immediateRender:false}},{ts[k]});")
    if lab:
        js.append(f"KW.enter(tl,'#{sid} .{sid}_lab','pop',{t0 + .2:.3f});")
    return "".join(h), js, [("counter", t) for t in ts[:4]]


def gen_network(sid, sp, t0, t1, R, wt):
    items = (sp.get("items") or ["", "", "", "", ""])[:6]
    n = max(3, len(items))
    cx, cy, rad = 540, 430, 330
    h = ['<svg class="abs" style="left:0;top:0" width="1080" height="880">']
    pos = []
    for k in range(n):
        a = 2 * math.pi * k / n + R.uniform(-.25, .25) - math.pi / 2
        rr = rad * R.uniform(.82, 1.05)
        pos.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        h.append(f'<path class="ln-draw {sid}_l{k}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" d="M{cx} {cy} L{pos[-1][0]:.0f} {pos[-1][1]:.0f}" stroke="rgba(255,255,255,.35)" stroke-width="3"/>')
    h.append(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="2"/></svg>')
    ts = item_times(sp, t0, t1, n, wt)
    js = []
    for k, (x, y) in enumerate(pos):
        a, b = R.choice(SKY)
        lab = items[k] if k < len(items) else ""
        h.append(f'<div class="{sid}_a{k}" style="position:absolute;left:{x - 55:.0f}px;top:{y - 55:.0f}px;width:110px;height:110px;border-radius:50%;'
                 f'background:linear-gradient(135deg,{a},{b});border:4px solid #fff;box-shadow:0 8px 30px rgba(0,0,0,.6)">'
                 + (f'<div style="position:absolute;top:118px;left:50%;transform:translateX(-50%);white-space:nowrap;font-weight:700;font-size:28px">{mark(lab)}</div>' if lab else "")
                 + "</div>")
        js.append(f"KW.draw(tl,'#{sid} .{sid}_l{k}',{ts[k] - .15:.3f},.3);KW.enter(tl,'#{sid} .{sid}_a{k}','pop',{ts[k]});")
    val = sp.get("value")
    cid = f"{sid}_v"
    h.append(f'<div class="pill red" style="left:{cx}px;top:{cy}px;transform:translate(-50%,-50%);font-size:52px;font-weight:900" id="{cid}">{esc(sp.get("center") or "")}</div>')
    js.insert(0, f"KW.enter(tl,'#{cid}','pop',{t0 + .05:.3f});")
    if val is not None:
        v = float(val)
        js.append(f"KW.count(tl,'#{cid}',{t0 + .1:.3f},{max(.6, (t1 - t0) * .6):.2f},0,{v},{1 if v < 100 and v != int(v) else 0},'{esc(sp.get('prefix', ''))}','{esc(sp.get('suffix', ''))}');")
    return "".join(h), js, [("reveal", t0 + .05)] + [("counter", t) for t in ts[:3]]


def gen_counter(sid, sp, t0, t1, R, wt):
    v = float(sp.get("value") or 100)
    pre, suf = sp.get("prefix", ""), sp.get("suffix", "")
    dec = 1 if v != int(v) and v < 100 else 0
    lab = sp.get("label") or ""
    font = 300 if len(f"{pre}{int(v):,}{suf}") <= 5 else 210
    h = [f'<div class="big" id="{sid}_n" style="top:{300 - font // 2}px;font-size:{font}px;font-variant-numeric:tabular-nums">{esc(pre)}{esc(int(v) if v == int(v) else v)}{esc(suf)}</div>',
         f'<div class="big serif {sid}_lab" style="top:{360 + font // 2}px;font-size:76px;color:var(--dim)">{mark(lab)}</div>',
         f'<div class="{sid}_bar" style="position:absolute;left:240px;top:{330 + font // 2}px;width:600px;height:8px;border-radius:4px;background:var(--red);transform-origin:left"></div>']
    dur = max(.6, min(1.6, (t1 - t0) * .5))
    js = [f"KW.count(tl,'#{sid}_n',{t0 + .1:.3f},{dur:.2f},0,{v},{dec},'{esc(pre)}','{esc(suf)}');",
          f"KW.grow(tl,'#{sid} .{sid}_bar',{t0 + .1:.3f},{dur:.2f});",
          f"KW.enter(tl,'#{sid} .{sid}_lab','rise',{t0 + dur:.3f});"]
    ticks = [round(t0 + .1 + dur * f, 3) for f in (.0, .33, .66)]
    return "".join(h), js, [("counter", t) for t in ticks] + [("ding", t0 + .1 + dur)]


def gen_compare(sid, sp, t0, t1, R, wt):
    L = sp.get("left") or {"title": "Wrong", "items": []}
    Rt = sp.get("right") or {"title": "Right", "items": []}
    h, js = [], []
    t_mid = round(t0 + (t1 - t0) * .45, 3)
    for side, d, x, good, tt in (("l", L, 70, False, t0 + .05), ("r", Rt, 560, True, t_mid)):
        col = "var(--hl4)" if good else "var(--red)"
        ic = "check" if good else "cross"
        h.append(f'<div class="card {sid}_{side}" style="left:{x}px;top:60px;width:450px;height:740px">'
                 f'<div style="position:absolute;left:0;right:0;top:34px;text-align:center;font-weight:900;font-size:50px">{mark(d.get("title", ""))}</div>'
                 f'<div class="ico" style="left:155px;top:140px;width:140px;height:140px">{icon_svg(ic, col, 2.6)}</div>')
        for k, it in enumerate((d.get("items") or [])[:4]):
            h.append(f'<div style="position:absolute;left:30px;right:30px;top:{330 + k * 96}px;padding:16px 20px;border-radius:14px;background:rgba(255,255,255,.06);font-size:32px;font-weight:700">{mark(it)}</div>')
        h.append("</div>")
        js.append(f"KW.enter(tl,'#{sid} .{sid}_{side}','{'slideR' if side == 'l' else 'slideL'}',{tt:.3f});KW.draw(tl,'#{sid} .{sid}_{side} path',{tt + .25:.3f},.4);")
    js.append(f"tl.to('#{sid} .{sid}_l',{{opacity:.45,scale:.95,duration:.3}},{t_mid + .2:.3f});")
    return "".join(h), js, [("swap", t_mid), ("ding", t_mid + .3)]


def gen_quote(sid, sp, t0, t1, R, wt):
    text = sp.get("text") or "*less* is more"
    size = 112 if len(text) < 18 else 88
    h = [f'<div class="big {sid}_q" style="top:300px;font-size:{size}px;font-weight:700;padding:0 80px;letter-spacing:-.03em">{words_markup(text)}</div>',
         f'<div class="{sid}_u" style="position:absolute;left:300px;top:{330 + int(size * 2.2)}px;width:480px;height:10px;border-radius:5px;background:var(--red);transform-origin:left"></div>']
    js = [f"tl.fromTo('#{sid} .{sid}_q .w',{{autoAlpha:0,y:16,filter:'blur(6px)'}},{{autoAlpha:1,y:0,filter:'blur(0px)',duration:.6,stagger:.09,ease:'back.out(1.15)',immediateRender:false}},{t0 + .05:.3f});",
          f"KW.grow(tl,'#{sid} .{sid}_u',{t0 + .5:.3f},.45);"]
    return "".join(h), js, [("draw", t0 + .5)]


def gen_bars(sid, sp, t0, t1, R, wt):
    vals = [max(5, min(100, float(v))) for v in (sp.get("values") or [30, 55, 80])][:6]
    labs = (sp.get("labels") or [""] * len(vals))[:len(vals)]
    n = len(vals)
    bw = min(150, 700 // n - 30)
    x0 = (1080 - (n * bw + (n - 1) * 34)) // 2
    ts = item_times(sp, t0, t1, n, wt)
    h, js = ['<div style="position:absolute;left:120px;top:760px;width:840px;height:4px;background:rgba(255,255,255,.4)"></div>'], []
    for k, (v, lb) in enumerate(zip(vals, labs)):
        hh = int(6.2 * v)
        col = "var(--red)" if k == n - 1 else "rgba(255,255,255,.85)"
        h.append(f'<div class="{sid}_b{k}" style="position:absolute;left:{x0 + k * (bw + 34)}px;top:{760 - hh}px;width:{bw}px;height:{hh}px;border-radius:14px 14px 0 0;background:{col};transform-origin:bottom"></div>'
                 f'<div class="{sid}_t{k}" style="position:absolute;left:{x0 + k * (bw + 34) - 20}px;width:{bw + 40}px;top:780px;text-align:center;font-weight:700;font-size:30px">{mark(lb)}</div>')
        js.append(f"KW.grow(tl,'#{sid} .{sid}_b{k}',{ts[k]},.45,'scaleY');KW.enter(tl,'#{sid} .{sid}_t{k}','rise',{ts[k] + .1:.3f},.3);")
    return "".join(h), js, [("counter", t) for t in ts]


def gen_browser(sid, sp, t0, t1, R, wt):
    title = sp.get("title") or "search"
    rows = (sp.get("rows") or ["", "", ""])[:5]
    h = [f'<div class="card {sid}_w" data-device="{sid}" style="left:90px;top:60px;width:900px;height:720px;border-radius:22px;overflow:hidden">'
         '<div style="position:absolute;left:0;right:0;top:0;height:64px;border-bottom:2px solid var(--stroke);display:flex;gap:12px;align-items:center;padding-left:24px">'
         '<span style="width:18px;height:18px;border-radius:50%;background:#ff5f57"></span><span style="width:18px;height:18px;border-radius:50%;background:#febc2e"></span>'
         '<span style="width:18px;height:18px;border-radius:50%;background:#28c840"></span>'
         f'<span style="margin-left:24px;padding:6px 26px;border-radius:10px;background:rgba(255,255,255,.08);font-size:26px;color:var(--dim)">{esc(title)}</span></div>']
    ts = item_times(sp, t0, t1, len(rows), wt)
    js = []
    for k, r in enumerate(rows):
        h.append(f'<div class="{sid}_r{k}" style="position:absolute;left:40px;right:40px;top:{110 + k * 118}px;height:96px;border-radius:14px;background:rgba(255,255,255,.05);display:flex;align-items:center;gap:22px;padding:0 22px">'
                 f'<span style="width:62px;height:62px;border-radius:12px;background:linear-gradient(135deg,{R.choice(SKY)[0]},{R.choice(SKY)[1]})"></span>'
                 f'<span style="font-weight:700;font-size:34px">{mark(r) if r else ""}</span>'
                 + ("" if r else f'<span style="width:{R.choice([300, 420, 360])}px;height:14px;border-radius:7px;background:rgba(255,255,255,.3)"></span>') + "</div>")
        js.append(f"KW.enter(tl,'#{sid} .{sid}_r{k}','rise',{ts[k]},.3);")
    hi = R.randrange(len(rows))
    h.append(f'<svg class="abs {sid}_cur" style="left:640px;top:{150 + hi * 118}px;width:54px;height:54px" viewBox="0 0 24 24"><path d="M4 3l15 8-7 2-3 7z" fill="#fff" stroke="#000" stroke-width="1"/></svg>')
    h.append("</div>")
    tc = round(min(t1 - .4, ts[-1] + .4), 3)
    js.append(f"tl.fromTo('#{sid} .{sid}_cur',{{autoAlpha:0,x:180,y:120}},{{autoAlpha:1,x:0,y:0,duration:.4,ease:'power2.out',immediateRender:false}},{tc - .4:.3f});"
              f"tl.to('#{sid} .{sid}_r{hi}',{{backgroundColor:'rgba(232,40,60,.35)',duration:.15}},{tc:.3f});")
    return "".join(h), js, [("tick", tc)]


def gen_chapter(sid, sp, t0, t1, R, wt):
    n = sp.get("n", 1)
    title = sp.get("title") or ""
    style = R.choice(["outline", "solid", "serif"])
    num = f"{int(n):02d}" if str(n).isdigit() else esc(n)
    css = {"outline": "color:transparent;-webkit-text-stroke:5px #fff",
           "solid": "color:#fff", "serif": "font-family:'IS',serif;font-style:italic;font-weight:400;color:#fff"}[style]
    h = [f'<div class="big {sid}_n" style="top:120px;font-size:420px;{css}">{num}</div>',
         f'<div class="big {sid}_t" style="top:600px;font-size:84px;font-weight:700;letter-spacing:-.03em">{mark(title)}</div>',
         f'<div class="{sid}_bar" style="position:absolute;left:340px;top:560px;width:400px;height:10px;border-radius:5px;background:var(--red);transform-origin:center"></div>']
    hit = round(t0 + .35, 3)
    js = [f"tl.fromTo('#{sid} .{sid}_n',{{autoAlpha:0,scale:1.6,filter:'blur(10px)'}},{{autoAlpha:1,scale:1,filter:'blur(0px)',duration:.7,ease:'expo.out',immediateRender:false}},{t0 + .02:.3f});",
          f"KW.grow(tl,'#{sid} .{sid}_bar',{hit:.3f},.35);KW.enter(tl,'#{sid} .{sid}_t','rise',{hit + .05:.3f});",
          (f"tl.to('#{sid} .{sid}_n',{{scale:1.05,duration:{max(.3, t1 - t0 - .5):.2f},ease:'sine.inOut'}},{t0 + .42:.3f});" if sp.get("hero") else "")]
    return "".join(h), js, [("chapter", hit)]


def gen_cta(sid, sp, t0, t1, R, wt):
    word = sp.get("word") or "GUIDE"
    sub = sp.get("sub") or "to get it"
    h = [f'<div class="big {sid}_h" style="top:40px;font-size:72px;font-weight:700;letter-spacing:-.03em">Comment <span style="color:var(--red2)">“<i class="serif">{esc(word)}</i>”</span><br>{mark(sub)}</div>']
    for k in range(5):
        x = 180 + (k % 3) * 250 + (k // 3) * 125
        y = 330 + (k // 3) * 260
        h.append(f'<div class="{sid}_p{k}" style="position:absolute;left:{x}px;top:{y}px;width:220px;height:290px;background:#fff;border-radius:6px;box-shadow:0 14px 40px rgba(0,0,0,.6);transform:rotate({R.uniform(-6, 6):.1f}deg)">'
                 + "".join(f'<div style="margin:{22 if j == 0 else 12}px 20px 0;height:9px;border-radius:4px;background:{"#e8283c" if j == 0 else "rgba(0,0,0,.25)"};width:{R.choice([70, 85, 60, 90])}%"></div>' for j in range(9))
                 + "</div>")
    js = [f"KW.typeWords(tl,'#{sid} .{sid}_h',{t0 + .05:.3f});" if False else f"KW.enter(tl,'#{sid} .{sid}_h','rise',{t0 + .05:.3f});",
          f"tl.fromTo('#{sid} [class*={sid}_p]',{{autoAlpha:0,y:200,rotation:-20}},{{autoAlpha:1,y:0,rotation:0,duration:.45,stagger:.09,ease:'back.out(1.4)',immediateRender:false}},{t0 + .35:.3f});"]
    return "".join(h), js, [("cta", t0 + .35)]


def gen_steps(sid, sp, t0, t1, R, wt):
    items = (sp.get("items") or ["start", "grow", "win"])[:5]
    n = len(items)
    ts = item_times(sp, t0, t1, n, wt)
    pts = [(150 + k * (780 / max(1, n - 1)), 760 - k * (620 / max(1, n - 1))) for k in range(n)]
    d = "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in pts)
    h = [f'<svg class="abs" style="left:0;top:0" width="1080" height="880"><path class="ln-draw {sid}_path" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" d="{d}" stroke="rgba(255,255,255,.7)" stroke-width="5" stroke-dasharray="1"/></svg>']
    js = [f"KW.draw(tl,'#{sid} .{sid}_path',{t0 + .05:.3f},{max(.5, ts[-1] - t0):.2f});"]
    for k, ((x, y), it) in enumerate(zip(pts, items)):
        h.append(f'<div class="{sid}_s{k}" style="position:absolute;left:{x - 26:.0f}px;top:{y - 26:.0f}px;width:64px;height:64px;border-radius:50%;background:{"var(--red)" if k == n - 1 else "#fff"};box-shadow:0 0 24px rgba(255,255,255,.5)"></div>'
                 f'<div class="pill {sid}_l{k}" style="left:{min(700, x + 50):.0f}px;top:{y - 44:.0f}px;font-size:46px">{mark(it)}</div>')
        js.append(f"KW.enter(tl,'#{sid} .{sid}_s{k}','pop',{ts[k]});KW.enter(tl,'#{sid} .{sid}_l{k}','slideL',{ts[k] + .05:.3f},.35);")
    return "".join(h), js, [("counter", t) for t in ts]


def gen_icon(sid, sp, t0, t1, R, wt):
    """an illustrated GLASS OBJECT, not a pictogram: glow, disc with rim light + highlight, drawn icon"""
    name = sp.get("icon") or "star"
    lab = sp.get("label") or ""
    acc = R.choice(["#ff4d5e", "#ffd23f", "#2ee6d6", "#b05cff"])
    h = [
         f'<div class="{sid}_disc px-far" style="position:absolute;left:300px;top:70px;width:480px;height:480px;border-radius:50%;'
         f'background:radial-gradient(circle at 35% 28%,rgba(255,255,255,.22),rgba(255,255,255,.04) 45%,rgba(0,0,0,.25) 100%),'
         f'linear-gradient(160deg,#1f1f27,#0c0c10);border:2px solid rgba(255,255,255,.22);'
         f'box-shadow:inset 0 2px 0 rgba(255,255,255,.25),inset 0 -30px 60px rgba(0,0,0,.5),0 30px 80px rgba(0,0,0,.6),0 0 60px {acc}44">'
         f'<div style="position:absolute;left:12%;top:6%;width:56%;height:26%;border-radius:50%;background:linear-gradient(180deg,rgba(255,255,255,.28),transparent)"></div></div>',
         f'<div class="ico {sid}_i px-near" style="left:385px;top:155px;width:310px;height:310px;filter:drop-shadow(0 0 14px {acc})">{icon_svg(name, acc, 1.5)}</div>']
    if lab:
        h.append(f'<div class="big {sid}_l" style="top:640px;font-size:72px;font-weight:700;letter-spacing:-.03em">{mark(lab)}</div>')
    js = [f"KW.glowIn(tl,'#{sid} .{sid}_halo',{t0:.3f});KW.enter(tl,'#{sid} .{sid}_disc','pop',{t0 + .05:.3f});",
          f"KW.draw(tl,'#{sid} .{sid}_i path',{t0 + .25:.3f},.8);"]
    if lab:
        js.append(f"KW.enter(tl,'#{sid} .{sid}_l','settle',{t0 + .55:.3f});")
    return "".join(h), js, [("glow", t0 + .3)]


def gen_chat(sid, sp, t0, t1, R, wt):
    msgs = (sp.get("messages") or [{"from": "in", "text": "hey"}])[:4]
    ts = item_times(sp, t0, t1, len(msgs), wt)
    h, js = [], []
    y = 80
    for k, m in enumerate(msgs):
        side = "out" if m.get("from") == "out" else "in"
        pos = "right:150px" if side == "out" else "left:150px"
        h.append(f'<div class="bubble {side} {sid}_m{k}" style="{pos};top:{y}px;font-size:54px;max-width:640px">{mark(m.get("text", ""))}</div>')
        y += 210
        js.append(f"KW.enter(tl,'#{sid} .{sid}_m{k}','{ 'slideL' if side == 'out' else 'slideR'}',{ts[k]},.35);")
    return "".join(h), js, [("tick", t) for t in ts]


def gen_custom_svg(sid, sp, t0, t1, R, wt):
    svg = sp.get("svg") or ""
    svg = re.sub(r"<\s*/?\s*(script|foreignObject|image|use|style|iframe)[^>]*>", "", svg, flags=re.I)
    svg = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg)
    svg = re.sub(r"(href|xlink:href)\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg)
    if "<svg" not in svg:
        svg = f'<svg viewBox="0 0 900 800">{svg}</svg>'
    svg = re.sub(r"<svg", '<svg class="abs" style="left:90px;top:40px;width:900px;height:800px;overflow:visible"', svg, count=1)
    # every stroked path draws; class p pops
    svg = re.sub(r"<path(?![^>]*pathLength)", '<path pathLength="1" stroke-dasharray="1"', svg)
    js = [f"tl.fromTo('#{sid} path',{{attr:{{'stroke-dashoffset':1}}}},{{attr:{{'stroke-dashoffset':0}},duration:.6,stagger:.06,ease:'power2.inOut',immediateRender:false}},{t0 + .05:.3f});",
          f"tl.fromTo('#{sid} .p, #{sid} text',{{autoAlpha:0,scale:.6,transformOrigin:'50% 50%'}},{{autoAlpha:1,scale:1,duration:.3,stagger:.08,ease:'back.out(2)',immediateRender:false}},{t0 + .4:.3f});"]
    lab = sp.get("label")
    h = svg + (f'<div class="big {sid}_l" style="top:800px;font-size:60px;font-weight:700">{mark(lab)}</div>' if lab else "")
    if lab:
        js.append(f"KW.enter(tl,'#{sid} .{sid}_l','rise',{t0 + .5:.3f});")
    return h, js, [("draw", t0 + .05)]


def gen_hero3d(sid, sp, t0, t1, R, wt):
    lab = sp.get("label") or ""
    h = f'<div class="big {sid}_l" style="top:780px;font-size:70px;font-weight:700;letter-spacing:-.03em">{mark(lab)}</div>' if lab else ""
    js = [f"KW.enter(tl,'#{sid} .{sid}_l','rise',{t0 + .4:.3f});"] if lab else []
    return h, js, [("reveal", t0 + .35)]


GEN = {k[4:]: v for k, v in globals().items() if k.startswith("gen_")}


# ----------------------------------------------------------------------------- 3D (three.js)
THREE_MODULE = r"""
<script type="importmap">{ "imports": { "three": "./assets/vendor/three/build/three.module.min.js", "three/addons/": "./assets/vendor/three/addons/" } }</script>
<script type="module">
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
const W = 1080, Hh = 1370, BEATS = __BEATS__;
const canvas = document.getElementById('gl3d');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, alpha: true });
renderer.setPixelRatio(1); renderer.setSize(W, Hh, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
const scene = new THREE.Scene();
{ const bc = document.createElement('canvas'); bc.width = W; bc.height = Hh; const b = bc.getContext('2d');
  b.fillStyle = getComputedStyle(document.body).classList ? '#0a0a0c' : '#0a0a0c';
  b.fillStyle = document.body.classList.contains('kw-light') ? '#e9e9ec' : '#0a0a0c'; b.fillRect(0, 0, W, Hh);
  b.strokeStyle = document.body.classList.contains('kw-light') ? 'rgba(0,0,0,.07)' : 'rgba(255,255,255,.055)'; b.lineWidth = 2;
  for (let x = -80 % 90 + 90; x < W; x += 90) { b.beginPath(); b.moveTo(x, 0); b.lineTo(x, Hh); b.stroke(); }
  for (let y = -80 % 90 + 90; y < Hh; y += 90) { b.beginPath(); b.moveTo(0, y); b.lineTo(W, y); b.stroke(); }
  const vg = b.createRadialGradient(W / 2, Hh * .48, Hh * .2, W / 2, Hh * .48, Hh * .7); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.5)');
  b.fillStyle = vg; b.fillRect(0, 0, W, Hh);
  const bt = new THREE.CanvasTexture(bc); bt.colorSpace = THREE.SRGBColorSpace; scene.background = bt; }
const pm = new THREE.PMREMGenerator(renderer);
scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = .6;
const cam = new THREE.PerspectiveCamera(36, W / Hh, .05, 100);
scene.add(new THREE.DirectionalLight(0xffffff, 1.2).translateX(3).translateY(5).translateZ(6));
const red = new THREE.PointLight(0xe8283c, 16, 14, 2); red.position.set(-3, 2, 3); scene.add(red);
const glassM = (c, o) => new THREE.MeshPhysicalMaterial({ color: c, roughness: .06, clearcoat: 1, clearcoatRoughness: .03, transparent: true, opacity: o, envMapIntensity: 1.3, depthWrite: false });
const metal = (c) => new THREE.MeshPhysicalMaterial({ color: c, metalness: 1, roughness: .22, clearcoat: .6, envMapIntensity: 1.3 });
const neon = (r, g, b) => new THREE.MeshBasicMaterial({ color: new THREE.Color(r, g, b), toneMapped: false });
const P = {};
// phone
P.phone = new THREE.Group();
P.phone.add(new THREE.Mesh(new RoundedBoxGeometry(1.5, 3.0, .2, 8, .2), new THREE.MeshPhysicalMaterial({ color: 0x050507, metalness: .7, roughness: .2, clearcoat: 1, envMapIntensity: .7 })));
const sc = document.createElement('canvas'); sc.width = 512; sc.height = 1024; const g = sc.getContext('2d');
g.fillStyle = '#0b0b10'; g.fillRect(0, 0, 512, 1024);
g.fillStyle = '#e8283c'; g.font = '900 92px PS, sans-serif'; g.textAlign = 'center'; g.fillText('@you', 256, 210);
g.fillStyle = '#ffffff'; g.font = '700 44px PS, sans-serif'; g.fillText('your page', 256, 280);
const cols = ['#ff6b6b', '#48dbfb', '#feca57', '#a29bfe', '#1dd1a1', '#fd79a8'];
for (let k = 0; k < 6; k++) { g.fillStyle = cols[k]; g.globalAlpha = .55; g.fillRect(40 + (k % 2) * 222, 340 + Math.floor(k / 2) * 215, 210, 200); }
g.globalAlpha = 1;
const st = new THREE.CanvasTexture(sc); st.colorSpace = THREE.SRGBColorSpace;
const scr = new THREE.Mesh(new THREE.PlaneGeometry(1.34, 2.7), new THREE.MeshBasicMaterial({ map: st, color: new THREE.Color(.95, .95, .95), toneMapped: false }));
scr.position.z = .102; P.phone.add(scr);
const halo = new THREE.Mesh(new RoundedBoxGeometry(1.56, 3.06, .05, 8, .22), neon(.55, .07, .12)); halo.position.z = -.09; P.phone.add(halo);
// coins
P.coins = new THREE.Group();
for (let k = 0; k < 7; k++) { const c = new THREE.Mesh(new THREE.CylinderGeometry(.55, .55, .12, 64), metal(0xffc53d)); c.position.y = -1 + k * .14; c.rotation.y = k * .3; P.coins.add(c); }
const top = new THREE.Mesh(new THREE.CylinderGeometry(.55, .55, .12, 64), metal(0xffd76a)); top.position.set(.9, .6, 0); top.rotation.x = 1.2; P.coins.add(top);
// ring
P.ring = new THREE.Group();
P.ring.add(new THREE.Mesh(new THREE.TorusGeometry(1.1, .28, 48, 200), glassM(0xd8102c, .32)));
P.ring.add(new THREE.Mesh(new THREE.TorusGeometry(1.1, .085, 24, 200), neon(2.4, .06, .16)));
// cube
P.cube = new THREE.Group();
P.cube.add(new THREE.Mesh(new RoundedBoxGeometry(1.7, 1.7, 1.7, 6, .16), glassM(0xffffff, .22)));
P.cube.add(new THREE.Mesh(new RoundedBoxGeometry(.8, .8, .8, 4, .1), neon(2.2, .1, .2)));
// bars
P.bars = new THREE.Group();
[.5, .9, 1.4, 2.1].forEach((h, k) => { const b = new THREE.Mesh(new RoundedBoxGeometry(.5, h, .5, 4, .06), k === 3 ? neon(2.2, .1, .2) : glassM(0xffffff, .5)); b.position.set(-1.05 + k * .7, -1.1 + h / 2, 0); P.bars.add(b); });
Object.values(P).forEach(g => { g.visible = false; scene.add(g); });
const composer = new EffectComposer(renderer); composer.setPixelRatio(1); composer.setSize(W, Hh);
composer.addPass(new RenderPass(scene, cam));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W / 2, Hh / 2), .32, .25, .97));
composer.addPass(new OutputPass());
const cl = (x) => Math.min(1, Math.max(0, x));
const back = (x) => { x = cl(x); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
let lastOn = false;
window.__kw3d = function (t) {
  let on = null;
  for (const b of BEATS) if (t >= b.t0 && t < b.t1) on = b;
  Object.values(P).forEach(g => g.visible = false);
  if (!on) { if (lastOn) { renderer.clear(); } lastOn = false; return; }
  lastOn = true;
  const g = P[on.preset] || P.cube; g.visible = true;
  const u = t - on.t0, k = back(u / .6), out = cl((on.t1 - t) / .3);
  g.scale.setScalar(Math.max(.001, (.3 + .7 * k) * (.6 + .4 * out)));
  g.rotation.set(.18 + .12 * Math.sin(u * .9), -1.0 * (1 - k) + .55 * Math.sin(u * .8 + on.spin), .04 * Math.sin(u));
  g.position.set(0, .35, 0);
  cam.position.set(.25 * Math.sin(u * .5), .2, 9.6 - .6 * cl(u / (on.t1 - on.t0)));
  cam.lookAt(0, .3, 0);
  composer.render();
};
window.__kw3dReady = true;
</script>
"""


# ----------------------------------------------------------------------------- composition
def beat_times(plan, words, total):
    """beat i starts at its first word (minus a lead), ends at the next beat."""
    bs = plan["beats"]
    starts = []
    for i, b in enumerate(bs):
        w0 = b.get("w0", 0)
        t = words[min(w0, len(words) - 1)]["t"] - .12 if words else 0
        starts.append(0.0 if i == 0 else max(0.0, t))
    for i in range(1, len(starts)):  # monotonic, >= 0.6 s per beat
        starts[i] = max(starts[i], starts[i - 1] + .6)
    ends = starts[1:] + [total]
    return [(round(a, 3), round(min(b, total), 3)) for a, b in zip(starts, ends)]


def captions(words, layout_at, emph, total, chunk_words=3, maxch=16):
    """1-3 word chunks (<= maxch chars), cut at punctuation; emphasised words -> serif italic."""
    caps, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        txt = " ".join(words[j]["w"] for j in cur)
        end = w["w"][-1:] in ".,?!:;" or len(cur) >= chunk_words or len(txt) >= maxch
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt and (nxt["t"] - w["e"] > .35):
            end = True
        if end:
            caps.append(cur)
            cur = []
    if cur:
        caps.append(cur)
    out = []
    for k, c in enumerate(caps):
        t0 = max(0, words[c[0]]["t"] - 2 / FPS)
        t1 = (words[caps[k + 1][0]]["t"] - 2 / FPS) if k + 1 < len(caps) else min(total, words[c[-1]]["e"] + .6)
        t1 = min(t1, words[c[-1]]["e"] + .9)
        parts = []
        for j in c:
            s = re.sub(r"[^\w'’%$#&@+\-]", "", words[j]["w"]) or words[j]["w"]
            s = s if s in ("I",) else s
            parts.append(f"<i>{esc(s)}</i>" if j in emph else esc(s))
        out.append((round(t0, 3), round(max(t0 + .1, t1), 3), " ".join(parts), layout_at((t0 + t1) / 2)))
    return out


def geometry(speaker_h=940):
    """layout as a function of the speaker card height (px of 1920). Round 1 = 528 (Kallaway);
    round 2 default 940: card y 960-1900, motion panel 0-958, seam caption just above the card."""
    speaker_h = int(max(500, min(1100, speaker_h)))
    card_y = 1900 - speaker_h
    panel_h = card_y - 2
    cap_top = panel_h - 104
    stage_top = 312 if panel_h >= 1100 else 300
    stage_h = cap_top - 16 - stage_top
    # ONE source of truth for the split layout: panel rect, card rect, corner radius, background colour, seam
    return dict(speaker_h=speaker_h, card_y=card_y, panel_h=panel_h, cap_top=cap_top, stage_top=stage_top, stage_h=stage_h,
                card_x=24, card_w=1032, radius=38, bg='#0a0a0c', bg_rgb=(10, 10, 12), seam=(panel_h + card_y) / 2)


ACC = ["#ff4d5e", "#ffd23f", "#2ee6d6", "#b05cff", "#3dff8b"]


def fx_layers(sid, t0, t1, R, hero, every_shine):
    return '', []  # removed for good (owner: no glow / particles / shine layers)
    """substance instead of text: light, particles and one cinematic shine — all settle to stillness."""
    acc = R.choice(ACC)
    n = 30 if hero else 14
    parts = []
    for k in range(n):
        ang = R.uniform(0, 6.283)
        r0 = R.uniform(120, 300)
        x, y = 540 + r0 * math.cos(ang), 430 + r0 * .8 * math.sin(ang)
        sz = R.choice([3, 4, 5, 6, 8])
        col = acc if k % 3 == 0 else "#ffffff"
        dist = R.uniform(30, 110)
        parts.append(f'<i class="pt" data-dx="{dist * math.cos(ang):.1f}" data-dy="{dist * .8 * math.sin(ang):.1f}" '
                     f'data-a="{R.uniform(.35, .9):.2f}" data-dl="{R.uniform(0, .35):.2f}" '
                     f'style="left:{x:.0f}px;top:{y:.0f}px;width:{sz}px;height:{sz}px;background:{col};box-shadow:0 0 {sz * 3}px {col}"></i>')
    html = (f'<div class="fx-glow {sid}_g" style="background:radial-gradient(ellipse 52% 46% at 50% 49%,{acc}2e 0%,{acc}12 40%,transparent 72%)"></div>'
            f'<div class="fx-pts px-far {sid}_p">{"".join(parts)}</div>')
    js = [f"KW.glowIn(tl,'#{sid} .{sid}_g',{t0:.3f});KW.burst(tl,'#{sid} .{sid}_p .pt',{t0 + .12:.3f});"]
    if hero:  # the cinematic shine is a hero privilege (motion budget: <= 25 % ambient motion in holds)
        html += f'<div class="fx-shine {sid}_sh"></div>'
        js.append(f"KW.shine(tl,'#{sid} .{sid}_sh',{max(t0 + .5, min(t1 - 1.35, t0 + .75)):.3f});")
    return html, js


def compile_reel(plan, words, total, ctx, chunk=None):
    """ctx: {seed, fonts_ok, theme, face_y (speaker caption y), has3d, audio}"""
    seed = int(plan.get("seed", ctx.get("seed", 1)))
    theme = plan.get("theme", "dark")
    acc2 = plan.get("accent2", "#ffd23f")
    bt = beat_times(plan, words, total)
    beats = plan["beats"]
    wt = lambda i: words[i]["t"] if 0 <= i < len(words) else None  # noqa
    lay = [(a, b, beats[k].get("layout", "split")) for k, (a, b) in enumerate(bt)]

    def layout_at(t):
        for a, b, l in lay:
            if a <= t < b:
                return l
        return lay[-1][2]

    G = ctx.get("geom") or geometry(ctx.get("speaker_h", 940))
    base_k = round(G["stage_h"] / 880, 4)  # generators draw in a 1080x880 frame
    body, js, cues, beats3d = [], [], [], []
    heads = []
    n_scene = 0
    prev_layout = None
    for k, (b, (t0, t1)) in enumerate(zip(beats, bt)):
        R = random.Random(seed * 1000 + k)
        L = b.get("layout", "split")
        sp = b.get("scene") or {}
        typ = sp.get("type", "icon") if L != "speaker" else None
        sid = f"s{k}"
        # layout switches
        if L != prev_layout:
            if L == "speaker":
                js.append(f"KW.hide(tl,'#panel',{t0:.3f});KW.hide(tl,'#gfx',{t0:.3f});KW.flash(tl,'#flash',{t0:.3f},.18);")
                cues.append(dict(t=t0, role="punch", why=f"beat {k} -> full speaker"))
            elif L == "graphic":
                js.append(f"KW.show(tl,'#panel',{t0:.3f});KW.show(tl,'#gfx',{t0:.3f});")
                cues.append(dict(t=t0, role="swap" if prev_layout == "split" else "back", why=f"beat {k} -> graphic"))
            else:
                js.append(f"KW.show(tl,'#panel',{t0:.3f});KW.hide(tl,'#gfx',{t0:.3f});")  # no panel slide: stillness
                if prev_layout is not None:
                    cues.append(dict(t=t0, role="back", why=f"beat {k} -> split"))
        prev_layout = L
        # header (persist until changed)
        hd = b.get("header")
        if hd and L != "speaker":
            hid = f"h{k}"
            style = hd.get("style", "plain")
            size = "lg" if len(hd.get("text", "")) < 16 else ("sm" if len(hd.get("text", "")) > 34 else "")
            body.append(f'<div class="hd {size} {"box" if style == "box" else ""}" id="{hid}">{words_markup(hd.get("text", ""))}</div>')
            if heads:
                ph = heads[-1]
                js.append(f"KW.exit(tl,'#{ph}','pushUp',{t0 - .05:.3f},.2);")
            js.append(f"KW.typeWords(tl,'#{hid}',{t0 + .02:.3f},{R.choice([.07, .09, .11])});")
            heads.append(hid)
        elif L == "speaker" and heads:
            js.append(f"KW.hide(tl,'#{heads[-1]}',{t0:.3f});")
            heads.append(None)
            heads.pop()
        if typ:
            gen = GEN.get(typ, GEN["icon"])
            hero = bool(b.get("hero") or sp.get("hero"))
            sp = dict(sp, hero=hero, _screen_fit=(ctx.get("screen_fit") or {}).get(sid))
            if typ == "hero3d":
                beats3d.append(dict(t0=t0, t1=t1, preset=sp.get("preset", "cube"), spin=R.uniform(0, 3)))
            h, j, cue = gen(sid, sp, t0, t1, R, wt)
            # every generator tween goes through KW.ft (FROM state guarded at scene start)
            j = [x.replace("tl.fromTo(", "KW.ft(tl,").replace(",immediateRender:false", "") for x in j]
            enter, exit_ = sp.get("enter", "settle"), sp.get("exit", "fade")
            camv = sp.get("camera", "none") if hero else "none"   # continuous motion = hero only
            fxh, fxj = fx_layers(sid, t0, t1, R, hero, n_scene % 3 == 1) if typ not in ("hero3d",) else ("", [])
            n_scene += 1
            fs = (ctx.get("fit") or {}).get(sid)
            wrap = f'<div class="abs" style="inset:0;transform:scale({fs});transform-origin:50% 50%">' if fs else "<div>"
            body.append(f'<div class="sc{" gfx" if L == "graphic" else ""}" id="{sid}"><div class="base" style="transform:scale({base_k if L != "graphic" else 1})">'
                        f'{wrap}<div class="cam" id="{sid}c">{fxh}{h}</div></div></div></div>')
            js.append(f"KW.scene({t0:.3f});")
            js.append(f"KW.enter(tl,'#{sid}','{enter}',{t0:.3f});")
            js.append(f"KW.camera(tl,'#{sid}c','{camv}',{t0:.3f},{t1:.3f});")
            js += fxj
            js += j
            js.append(f"KW.exit(tl,'#{sid}','{exit_}',{max(t0 + .3, t1 - .34):.3f},.32);")
            for role, t in cue:
                cues.append(dict(t=round(t, 3), role=role, why=f"beat {k} {typ}", run=f"r{k}" if role == "counter" else None))
        for extra in b.get("sfx", []) or []:
            if isinstance(extra, str):
                cues.append(dict(t=t0, role=extra, why=f"planner hint beat {k}", prio=3))
                if extra == "flash":
                    js.append(f"KW.flash(tl,'#flash',{t0:.3f},.5);")
    cues.insert(0, dict(t=round(min(1.0, bt[1][0] if len(bt) > 1 else .8) - .02, 3), role="intro", why="reel open"))

    emph = set(plan.get("emph", []))
    caps = captions(words, layout_at, emph, total)
    face_y = ctx.get("face_cap_y", 1180)
    cap_html = []
    for i, (a, b, txt, L) in enumerate(caps):
        if chunk and (b <= chunk[0] or a >= chunk[0] + chunk[1]):
            continue
        cls = "cap seam" if L == "split" else "cap full"
        top = "" if L == "split" else f"top:{face_y if L == 'speaker' else 1180}px"
        st = a - (chunk[0] if chunk else 0)
        du = b - a
        if chunk:
            st2 = max(0, st)
            du = min(b - (chunk[0]), chunk[1]) - st2
            st = st2
        cap_html.append(f'<div class="clip {cls}" id="c{i}" style="{top}" data-start="{st:.3f}" data-duration="{max(.04, du):.3f}" data-track-index="3">{txt}</div>')
        js.append(f"KW.cap(tl,'#c{i}',{a:.3f});")

    off, dur = (chunk if chunk else (0.0, total))
    # <video> costs ~40 ms/frame in the renderer. In "speaker_only" mode the page carries video ONLY
    # during full-screen speaker runs; the split card band (y >= 1370, nothing drawn over it) is
    # composited from assets/video.mp4 by ffmpeg in the chunk crop pass (render.py).
    vstyle = 'style="position:absolute;left:0;top:0;width:1080px;height:2040px"'
    if ctx.get("video_mode") == "speaker_only":
        runs = []
        for a_, b_, l_ in lay:
            if l_ == "speaker":
                if runs and abs(runs[-1][1] - a_) < 1e-3:
                    runs[-1][1] = b_
                else:
                    runs.append([a_, b_])
        vids = []
        for k, (a_, b_) in enumerate(runs):
            a2, b2 = max(a_, off), min(b_, off + dur)
            if b2 - a2 < 1 / FPS:
                continue
            vids.append(f'<video id="vid{k}" class="clip" src="assets/video.mp4" data-start="{a2 - off:.3f}" data-duration="{b2 - a2:.3f}" '
                        f'data-media-start="{a2:.3f}" data-track-index="0" muted playsinline {vstyle}></video>')
        video_html = "\n".join(vids)
    else:
        video_html = (f'<video id="vid" class="clip" src="assets/video.mp4" data-start="0" data-duration="{dur:.3f}" '
                      f'data-media-start="{off:.3f}" data-track-index="0" muted playsinline {vstyle}></video>')
    css = open(os.path.join(RT, "kw.css")).read()
    kw = open(os.path.join(RT, "kw.js")).read()
    has3d = bool(beats3d)
    tl_js = "\n".join(js)
    if has3d:
        tl_js += f"\nconst P3={{t:0}};tl.fromTo(P3,{{t:0}},{{t:{total:.3f},duration:{total:.3f},ease:'none',immediateRender:false,onUpdate:()=>{{if(window.__kw3d)window.__kw3d(P3.t)}}}},0);"
        tl_js += "\n" + "".join(f"KW.show(tl,'#gl3d',{b['t0']:.3f});KW.hide(tl,'#gl3d',{b['t1']:.3f});" for b in beats3d)
    reg = (f"const W=gsap.timeline({{paused:true}});W.fromTo(tl,{{time:{off:.4f}}},{{time:{off + dur:.4f},duration:{dur:.4f},ease:'none',immediateRender:true}},0);"
           "window.__timelines=window.__timelines||{};window.__timelines['main']=W;") if chunk else \
        "window.__timelines=window.__timelines||{};window.__timelines['main']=tl;"
    audio = "" if chunk or not ctx.get("audio") else \
        f'<audio id="aud" class="clip" src="{ctx["audio"]}" data-start="0" data-duration="{total:.3f}" data-track-index="8"></audio>'
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080, height=2040">
<title>{esc(plan.get('title', 'split-motion reel'))}</title>
<script src="assets/vendor/gsap.min.js"></script>
<style>{css}
:root {{ --acc2: {acc2}; --panel-h: {G["panel_h"]}px; --cap-top: {G["cap_top"]}px; --stage-top: {G["stage_top"]}px; --stage-h: {G["stage_h"]}px; }}
</style></head>
<body class="{'kw-light' if theme == 'light' else ''}">
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-width="1080" data-height="2040">
{video_html}
<div id="panel" class="clip" data-start="0" data-duration="{dur:.3f}" data-track-index="2" data-layout-allow-overflow>
 <div id="panelbg"><div class="grid"></div><div class="vig"></div></div>
 <div id="gfx"><div class="grid"></div></div>
 {f'<canvas id="gl3d" width="1080" height="{G["panel_h"]}"></canvas>' if has3d else ''}
 {''.join(body)}
</div>
{''.join(cap_html)}
<div id="flash" class="clip" data-start="0" data-duration="{dur:.3f}" data-track-index="4"></div>
{audio}
</div>
<script>{kw}</script>
<script>
const tl = gsap.timeline({{paused:true}});
gsap.set('#panel',{{autoAlpha:{1 if lay[0][2] != 'speaker' else 0}}});
{tl_js}
tl.set({{}},{{}},{total:.3f});
{reg}
</script>
{THREE_MODULE.replace('__BEATS__', json.dumps(beats3d)).replace('Hh = 1370', 'Hh = ' + str(G["panel_h"])) if has3d else ''}
</body></html>"""
    meta_beats = [dict(hero=bool(beats[k].get("hero") or (beats[k].get("scene") or {}).get("hero")), sid=(f"s{k}" if beats[k].get("layout", "split") != "speaker" else None), t0=a, t1=b,
                       layout=beats[k].get("layout", "split"), type=(beats[k].get("scene") or {}).get("type"))
                  for k, (a, b) in enumerate(bt)]
    return html, cues, meta_beats, caps


def beat_words(plan, words):
    """word index ranges per beat (for the duplicate-text validator)"""
    ws = [b.get("w0", 0) for b in plan["beats"]] + [len(words)]
    return [(ws[k], ws[k + 1]) for k in range(len(plan["beats"]))]
