#!/usr/bin/env python3
"""Compose round-3 sections (bespoke GSAP from the scene coder) into a HyperFrames page.

compose(story, codes, words, total, ctx, chunk=None) -> (html, cues, beats)
  story = director storyboard with sections already on the CUT word index (s["w0"], s["w1"]),
          speaker runs story["speaker"] = [[w0, w1], ...] (full-screen speaker, panel hidden)
  codes = {section_id: JS body}   (written by coder.py; runs with ctx/R3/tl/W/S/E/G in scope)
Transitions by transformation: consecutive sections OVERLAP by 0.45 s — the outgoing one pushes
through (scale up + motion blur) while the incoming one arrives (scale .94 -> 1, blur -> 0),
so there is never a blank panel between sections.
"""
import html as H
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import scenes  # noqa: E402  (captions, geometry, words_markup, THREE-free helpers)

OVL = .45


def section_times(story, words, total):
    secs = story["sections"]
    out = []
    for k, s in enumerate(secs):
        t0 = 0.0 if k == 0 else max(0.0, words[min(s["w0"], len(words) - 1)]["t"] - .15)
        out.append(t0)
    ends = out[1:] + [total]
    return [(round(a, 3), round(b, 3)) for a, b in zip(out, ends)]


def speaker_runs(story, words, total):
    runs = []
    for a, b in story.get("speaker", []):
        if a >= len(words):
            continue
        t0 = max(0, words[a]["t"] - .1)
        t1 = (words[b + 1]["t"] - .1) if b + 1 < len(words) else total
        if t1 - t0 >= .8:
            runs.append((round(t0, 3), round(t1, 3)))
    return runs


def compose(story, codes, words, total, ctx, chunk=None):
    G = ctx["geom"]
    st = section_times(story, words, total)
    spk = speaker_runs(story, words, total)
    W = [round(w["t"], 3) for w in words]
    layout_at = lambda t: "speaker" if any(a <= t < b for a, b in spk) else "split"  # noqa: E731
    body, js, cues = [], [], []
    for k, (s, (t0, t1)) in enumerate(zip(story["sections"], st)):
        sid = f"sec{k}"
        hd = dict(s.get("header") or {})
        if hd.get("text"):
            hd["text"] = re.sub(r"\s*\[\s*red\s*box\s*\]", "", hd["text"], flags=re.I).strip()
        if hd.get("text"):
            body.append(f'<div class="hd" id="h{k}">{scenes.words_markup(hd["text"])}</div>')
        body.append(f'<div class="r3-sec" id="{sid}"><div class="r3-light"></div><div class="r3-cam" id="{sid}c">'
                    f'<div class="r3-layer" id="{sid}m"></div><div class="r3-layer" id="{sid}f"></div></div><div class="r3-vign"></div></div>')
        a_in = t0 if k == 0 else t0 - OVL
        e_out = t1 if k == len(st) - 1 else t1
        code = codes.get(sid, "")
        js.append(f"""
(function(){{ const sec=document.getElementById('{sid}'); const S={t0:.3f}, E={t1:.3f};
 const ctx=R3.begin({{sec, mid:document.getElementById('{sid}m'), fg:document.getElementById('{sid}f'), camEl:document.getElementById('{sid}c'), tl, S, E, W, G}});
 R3.light({json.dumps(s.get('light') or {})});
 try {{ (function(ctx,R3,tl,W,S,E,G){{
{code}
 }})(ctx,R3,tl,W,S,E,G); }} catch(e) {{ (window.__r3err=window.__r3err||[]).push('{sid}: '+e.message); }}
 tl.set(sec,{{autoAlpha:1}},{a_in:.3f});
 {"" if k == 0 else f"tl.fromTo(sec,{{scale:.94,filter:'blur(8px)'}},{{scale:1,filter:'blur(0px)',duration:{OVL + .15},ease:'power3.out',immediateRender:false}},{a_in:.3f});"}
 {"" if k == len(st) - 1 else f"tl.to(sec,{{scale:1.06,filter:'blur(10px)',autoAlpha:0,duration:{OVL},ease:'power2.in'}},{e_out - OVL:.3f}); tl.set(sec,{{autoAlpha:0}},{e_out + .02:.3f});"}
 {f"KW.typeWords(tl,'#h{k}',{t0 + .05:.3f},.08); KW.exit(tl,'#h{k}','lift',{t1 - .3:.3f},.28);" if hd.get('text') else ""}
}})();""")
        cues.append(dict(t=round(t0 + .05, 3), role="chapter" if k else "intro", why=f"section {k} hero arrives"))
        for ev in s.get("events", []):
            wi = ev.get("w")
            if wi is None or wi >= len(words):
                continue
            tt = words[wi]["t"]
            if not (t0 + .3 < tt < t1 - .2):
                continue
            role = "reveal" if ev.get("kind") == "major" else ("counter" if ev.get("kind") == "item" else "tick")
            cues.append(dict(t=round(tt, 3), role=role, why=f"section {k}: {ev.get('what', '')[:40]}", run=f"s{k}" if role == "counter" else None))
    # speaker runs hide the panel (and headers) — the card band / full speaker come from the video
    for a, b in spk:
        js.append(f"KW.hide(tl,'#panel',{a:.3f});KW.flash(tl,'#flash',{a:.3f},.16);KW.show(tl,'#panel',{b:.3f});")
        cues.append(dict(t=a, role="punch", why="full speaker"))
        cues.append(dict(t=b, role="back", why="back to panel"))
    caps = scenes.captions(words, layout_at, set(story.get("emph", [])), total)
    off, dur = chunk if chunk else (0.0, total)
    cap_html = []
    for i, (a, b, txt, L) in enumerate(caps):
        if chunk and (b <= off or a >= off + dur):
            continue
        cls = "cap seam" if L == "split" else "cap full"
        top = "" if L == "split" else f"top:{ctx.get('face_cap_y', 1180)}px"
        s0 = max(0, a - off) if chunk else a
        du = (min(b - off, dur) - s0) if chunk else b - a
        cap_html.append(f'<div class="clip {cls}" id="c{i}" style="{top}" data-start="{s0:.3f}" data-duration="{max(.04, du):.3f}" data-track-index="3">{txt}</div>')
        js.append(f"KW.cap(tl,'#c{i}',{a:.3f});")
    vstyle = 'style="position:absolute;left:0;top:0;width:1080px;height:2040px"'
    vids = []
    for k, (a, b) in enumerate(spk):
        a2, b2 = max(a, off), min(b, off + dur)
        if b2 - a2 >= 1 / 30:
            vids.append(f'<video id="vid{k}" class="clip" src="assets/video.mp4" data-start="{a2 - off:.3f}" data-duration="{b2 - a2:.3f}" '
                        f'data-media-start="{a2:.3f}" data-track-index="0" muted playsinline {vstyle}></video>')
    if not chunk and ctx.get("full_video"):
        vids = [f'<video id="vid" class="clip" src="assets/video.mp4" data-start="0" data-duration="{total:.3f}" data-track-index="0" muted playsinline {vstyle}></video>']
    css = open(os.path.join(scenes.RT, "kw.css")).read() + open(os.path.join(HERE, "r3.css")).read()
    kw = open(os.path.join(scenes.RT, "kw.js")).read()
    lib = open(os.path.join(HERE, "lib.js")).read()
    bg_js = ("const B=document.querySelectorAll('.r3-bg .field');"
             f"tl.fromTo(B[0],{{x:-80,y:-40}},{{x:80,y:40,duration:{total:.3f},ease:'sine.inOut',immediateRender:false}},0);"
             f"tl.fromTo(B[1],{{x:60,y:30}},{{x:-60,y:-30,duration:{total:.3f},ease:'sine.inOut',immediateRender:false}},0);")
    reg = (f"const WW=gsap.timeline({{paused:true}});WW.fromTo(tl,{{time:{off:.4f}}},{{time:{off + dur:.4f},duration:{dur:.4f},ease:'none',immediateRender:true}},0);"
           "window.__timelines=window.__timelines||{};window.__timelines['main']=WW;") if chunk else \
        "window.__timelines=window.__timelines||{};window.__timelines['main']=tl;"
    audio = "" if chunk or not ctx.get("audio") else \
        f'<audio id="aud" class="clip" src="{ctx["audio"]}" data-start="0" data-duration="{total:.3f}" data-track-index="8"></audio>'
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080, height=2040">
<title>{H.escape(story.get('title', 'split-motion r3'))}</title>
<script src="assets/vendor/gsap.min.js"></script>
<style>{css}
:root {{ --panel-h: {G["panel_h"]}px; --cap-top: {G["cap_top"]}px; --stage-top: {G["stage_top"]}px; --stage-h: {G["stage_h"]}px; }}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-width="1080" data-height="2040">
{''.join(vids)}
<div id="panel" class="clip" data-start="0" data-duration="{dur:.3f}" data-track-index="2" data-layout-allow-overflow>
 <div class="r3-bg"><div class="grid"></div><div class="field" style="left:-200px;top:-260px;background:radial-gradient(circle,rgba(255,170,110,.20),transparent 65%)"></div>
 <div class="field" style="left:420px;top:180px;background:radial-gradient(circle,rgba(120,150,255,.14),transparent 65%)"></div></div>
 {''.join(body)}
</div>
{''.join(cap_html)}
<div id="flash" class="clip" data-start="0" data-duration="{dur:.3f}" data-track-index="4"></div>
{audio}
</div>
<script>{kw}</script>
<script>{lib}</script>
<script>
const tl = gsap.timeline({{paused:true}});
const W = {json.dumps(W)};
const G = {json.dumps(dict(W=1080, H=G["panel_h"], top=G["stage_top"], bottom=G["cap_top"] - 16))}; window.G = G;
gsap.set('#panel',{{autoAlpha:1}});
{bg_js}
{''.join(js)}
tl.set({{}},{{}},{total:.3f});
{reg}
</script>
</body></html>"""
    beats = [dict(sid=f"sec{k}", t0=a, t1=b, layout="split", type=s.get("hero", {}).get("structure", "")) for k, (s, (a, b)) in enumerate(zip(story["sections"], st))]
    # speaker runs as beats too (for QC windows)
    for a, b in spk:
        beats.append(dict(sid=None, t0=a, t1=b, layout="speaker", type=None))
    beats.sort(key=lambda x: x["t0"])
    return html, cues, beats, caps, st, spk
