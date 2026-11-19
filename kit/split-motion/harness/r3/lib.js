/* ============================================================================
   R3 — component helper library for the round-3 scene layer (window.R3)
   The scene CODER (Claude) writes bespoke GSAP per section and uses these helpers.
   Helpers are building blocks, not a menu: compose, nest, restyle, add your own DOM.

   Contract for a section:  function (ctx) { ... }   with
     ctx = { sec, mid, fg, tl, S, E, W, G, light, cam, R3 }
       W[i]  = start time (s) of cut word i (absolute reel time)    S/E = section start/end
       G     = { W: 1080, H: panel height, top: 300 (below header), bottom: caption top - 16 }
   Rules baked in: deterministic (no random/Date), every tween's FROM state is applied at S
   (no final-state flashes), stroke draws use the SVG attribute, one light model per section
   (key light + bloom; cards get rim light + sheen from the SAME key direction).
   ============================================================================ */
(function () {
  const IR = { immediateRender: false };
  const TEMP = { warm: '255,176,112', cool: '127,184,255', neutral: '255,255,255', red: '255,77,94', gold: '255,205,90', green: '80,255,160', violet: '176,120,255' };
  let C = null; // current section ctx

  function mk(tag, cls, css, parent, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (css) Object.assign(e.style, css);
    if (html != null) e.innerHTML = html;
    (parent || C.mid).appendChild(e);
    return e;
  }
  const px = (v) => (typeof v === 'number' ? v + 'px' : v);
  const box = (x, y, w, h) => ({ left: px(x), top: px(y), width: px(w), height: px(h) });
  // fromTo with the FROM state guarded at section start
  function ft(target, from, to, t) {
    const tl = C.tl;
    if (t > C.S + 1e-3) tl.set(target, from, C.S);
    return tl.fromTo(target, from, Object.assign({}, to, IR), t);
  }
  function svgEl(tag, attrs, parent) {
    const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    parent.appendChild(e);
    return e;
  }
  function svgLayer(parent) {
    const s = svgEl('svg', { width: 1080, height: C.G.H, class: 'r3-svg' }, parent || C.mid);
    return s;
  }

  // ---------------- light model: ONE key light per section ----------------
  function light(o) {
    o = Object.assign({ x: 760, y: 120, temp: 'warm', bloom: .26, ambient: .07 }, o || {});
    const rgb = TEMP[o.temp] || o.temp;
    C.lightModel = { x: o.x, y: o.y, rgb };
    // NO background bloom/halo: light lives only in the content (rim, sheen, offset shadows)
    return C.lightModel;
  }
  // rim light + sheen on a card, from the section key light
  function lit(el, x, y, w, h, k = 1) {
    const L = C.lightModel || { x: 760, y: 120, rgb: TEMP.warm };
    let dx = L.x - (x + w / 2), dy = L.y - (y + h / 2);
    const n = Math.hypot(dx, dy) || 1; dx /= n; dy /= n;
    const ang = Math.round(Math.atan2(dy, dx) * 180 / Math.PI + 90);
    el.style.setProperty('--rimshadow', `inset ${(-dx * 12).toFixed(1)}px ${(-dy * 12).toFixed(1)}px 22px -12px rgba(${L.rgb},${.55 * k}), ${(dx * -18).toFixed(0)}px ${(dy * -18 + 20).toFixed(0)}px 50px rgba(0,0,0,.5)`);
    el.style.setProperty('--sheen', `linear-gradient(${ang + 180}deg, rgba(${L.rgb},${.13 * k}) 0%, transparent 42%)`);
    return el;
  }
  function card(x, y, w, h, parent, extra) {
    const e = mk('div', 'r3-card r3-el', Object.assign(box(x, y, w, h), extra || {}), parent);
    return lit(e, x, y, w, h);
  }

  // ---------------- motion verbs ----------------
  // group entrance: stagger + soft overshoot (+ a touch of motion blur on bigger moves)
  function appear(els, t, o) {
    o = Object.assign({ d: .55, stagger: .07, y: 24, x: 0, scale: .96, blur: 0, ease: 'back.out(1.2)' }, o || {});
    const from = { autoAlpha: 0, y: o.y, x: o.x, scale: o.scale }, to = { autoAlpha: 1, y: 0, x: 0, scale: 1, duration: o.d, ease: o.ease, stagger: o.stagger };
    if (o.blur) { from.filter = `blur(${o.blur}px)`; to.filter = 'blur(0px)'; }
    ft(els, from, to, t);
    return t + o.d + (Array.isArray(els) || els.length ? (els.length - 1) * o.stagger : 0);
  }
  function leave(els, t, o) { o = Object.assign({ d: .35 }, o || {}); C.tl.to(els, { autoAlpha: 0, y: -10, duration: o.d, ease: 'power2.in', stagger: o.stagger || 0 }, t); }
  function dim(els, t, a = .32) { C.tl.to(els, { opacity: a, duration: .4, ease: 'sine.inOut' }, t); }
  function pulse(el, t) { C.tl.fromTo(el, { scale: 1 }, { scale: 1.05, duration: .16, yoyo: true, repeat: 1, ease: 'sine.inOut', ...IR }, t); }
  function draw(path, t, d = .6) { ft(path, { attr: { 'stroke-dashoffset': 1 } }, { attr: { 'stroke-dashoffset': 0 }, duration: d, ease: 'power2.inOut' }, t); }
  function count(el, t, d, from, to, o) {
    o = Object.assign({ dec: 0, pre: '', suf: '' }, o || {});
    const p = { v: from }, f = (v) => o.pre + (o.dec ? v.toFixed(o.dec) : Math.round(v).toLocaleString('en-US')) + o.suf;
    C.tl.set(el, { textContent: f(from) }, C.S);
    ft(p, { v: from }, { v: to, duration: d, ease: 'power3.out', onUpdate: () => { el.textContent = f(p.v); } }, t);
  }
  // connector between two points (or elements' centres), drawn at t
  function connect(a, b, t, o) {
    o = Object.assign({ color: 'rgba(255,255,255,.55)', w: 3, curve: .35, d: .5 }, o || {});
    const P = (q) => (q.nodeType ? (() => { const x = parseFloat(q.style.left) + parseFloat(q.style.width) / 2, y = parseFloat(q.style.top) + parseFloat(q.style.height) / 2; return [x, y]; })() : q);
    const [x1, y1] = P(a), [x2, y2] = P(b), mx = (x1 + x2) / 2, my = (y1 + y2) / 2 - Math.abs(x2 - x1) * o.curve * .4;
    const s = o.svg || C._svg || (C._svg = svgLayer(C.mid));
    const p = svgEl('path', { d: `M${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`, fill: 'none', stroke: o.color, 'stroke-width': o.w, 'stroke-linecap': 'round',
      pathLength: 1, 'stroke-dasharray': 1, 'stroke-dashoffset': 1 }, s);
    draw(p, t, o.d);
    return p;
  }
  function chip(x, y, text, t, o) {
    o = o || {};
    const e = mk('div', 'r3-chip r3-el' + (o.red ? ' red' : ''), { left: px(x), top: px(y) }, o.parent, text);
    if (t != null) appear(e, t, { y: 10, scale: .9 });
    return e;
  }
  function text(x, y, html, o) {
    o = Object.assign({ size: 44, weight: 700, color: '#fff', align: 'left' }, o || {});
    const e = mk('div', 'r3-t r3-el', { left: px(x), top: px(y), fontSize: px(o.size), fontWeight: o.weight, color: o.color, textAlign: o.align,
      width: o.w ? px(o.w) : 'auto' }, o.parent, html);
    return e;
  }
  function number(x, y, value, o) {
    o = Object.assign({ size: 150 }, o || {});
    const e = mk('div', 'r3-num r3-el', { left: px(x), top: px(y), fontSize: px(o.size) }, o.parent, (o.pre || '') + value + (o.suf || ''));
    return e;
  }
  const SKY = [['#ff6b6b', '#5f27cd'], ['#feca57', '#ff6b6b'], ['#48dbfb', '#0abde3'], ['#1dd1a1', '#10ac84'], ['#a29bfe', '#6c5ce7'],
    ['#fd79a8', '#e84393'], ['#fab1a0', '#e17055'], ['#81ecec', '#00cec9'], ['#ffeaa7', '#fdcb6e'], ['#74b9ff', '#0984e3']];
  function thumb(x, y, w, h, k, o) {
    o = o || {};
    const [a, b] = SKY[k % SKY.length];
    const e = mk('div', 'r3-thumb r3-el', Object.assign(box(x, y, w, h), { background: `linear-gradient(${130 + (k * 37) % 90}deg, ${a}, ${b})` }), o.parent,
      (o.play === false ? '' : '<i class="p"></i>') + (o.views ? `<span class="v">${o.views}</span>` : ''));
    return e;
  }
  function avatar(x, y, d, k, parent) {
    const [a, b] = SKY[(k + 3) % SKY.length];
    return mk('div', 'r3-ava r3-el', Object.assign(box(x, y, d, d), { background: `radial-gradient(circle at 40% 35%, ${a}, ${b})` }), parent);
  }

  // ---------------- hero structures (each returns handles + evolution methods) ----------------
  // script / plan document whose highlighter rows build
  function doc(o) {
    o = Object.assign({ x: 250, y: 300, w: 580, h: 520, title: 'Video Script', rows: [] }, o);
    const c = card(o.x, o.y, o.w, o.h);
    const ttl = text(0, 24, o.title, { size: 34, parent: c, w: o.w, align: 'center' }); ttl.classList.add('r3-serif');
    const rows = o.rows.map((r, i) => {
      const y = 92 + i * ((o.h - 120) / Math.max(4, o.rows.length));
      const col = r.color || ['#ffd23f', '#b05cff', '#2ee6d6', '#3dff8b', '#ff5c8a', '#e8283c'][i % 6];
      const lab = text(32, y, `<span style="display:inline-block;width:16px;height:16px;border-radius:4px;background:${col};margin-right:12px"></span>${r.label || ''}`, { size: 24, parent: c });
      const bars = [0, 1].map((j) => mk('div', 'r3-bar r3-el', { left: '32px', top: px(y + 36 + j * 20), width: px((o.w - 64) * (j ? .62 : .9)), height: '12px', background: col, opacity: .9 }, c));
      return { lab, bars };
    });
    for (let j = 0; j < 7; j++) mk('div', 'r3-line r3-el', { left: '32px', top: px(o.h - 28 - j * 18), width: px((o.w - 64) * (.5 + .5 * ((j * 7) % 5) / 4)) }, c);
    return { el: c, rows,
      row(i, t) { const r = rows[i]; if (!r) return; appear(r.lab, t, { y: 8, d: .4 }); ft(r.bars, { scaleX: 0 }, { scaleX: 1, duration: .55, ease: 'power3.out', stagger: .08 }, t + .05); },
      highlight(i, t) { rows.forEach((r, j) => C.tl.to([r.lab, ...r.bars], { opacity: j === i ? 1 : .3, duration: .35 }, t)); } };
  }
  // phone with a feed of real-looking cards
  function phone(o) {
    o = Object.assign({ x: 330, y: 280, w: 420, h: 560, handle: '@you', cards: [] }, o);
    const c = card(o.x, o.y, o.w, o.h, null, { borderRadius: '54px', border: '4px solid rgba(255,255,255,.8)' });
    const scr = mk('div', 'r3-screen', box(12, 12, o.w - 24, o.h - 24), c); scr.dataset.device = '1';
    mk('div', '', Object.assign(box((o.w - 24) / 2 - 55, 8, 110, 28), { position: 'absolute', borderRadius: '16px', background: '#000' }), scr);
    text(24, 52, o.handle, { size: 22, parent: scr, color: 'rgba(255,255,255,.7)' });
    const feed = mk('div', '', { position: 'absolute', left: '0', top: '92px', width: '100%' }, scr);
    const cw = o.w - 48;
    const cards = o.cards.map((k, i) => {
      const e = mk('div', 'r3-el', Object.assign(box(12, i * 150, cw, 136), { position: 'absolute', borderRadius: '16px', background: 'rgba(255,255,255,.07)',
        border: '1px solid rgba(255,255,255,.12)', overflow: 'hidden' }), feed);
      thumb(10, 10, 116, 116, i + 2, { parent: e, views: k.views });
      text(140, 18, k.title || '', { size: 22, parent: e, w: cw - 150 }).style.whiteSpace = 'normal';
      text(140, 88, k.meta || '', { size: 18, parent: e, color: 'rgba(255,255,255,.55)' });
      return e;
    });
    return { el: c, screen: scr, feed, cards,
      card(i, t) { appear(cards[i], t, { y: 30 }); },
      scroll(t, n, d = .7) { C.tl.to(feed, { y: -150 * n, duration: d, ease: 'power3.inOut' }, t); } };
  }
  // creator profile: avatar, stats, post grid that fills
  function profile(o) {
    o = Object.assign({ x: 240, y: 290, w: 600, h: 540, name: 'Creator', handle: '@creator', posts: 0, followers: 0, cols: 3, rows: 3 }, o);
    const c = card(o.x, o.y, o.w, o.h);
    avatar(28, 24, 96, 1, c);
    text(140, 34, o.name, { size: 32, parent: c }); text(140, 76, o.handle, { size: 22, parent: c, color: 'rgba(255,255,255,.55)' });
    const stats = {};
    ['posts', 'followers'].forEach((k, i) => {
      stats[k] = text(o.w - 300 + i * 150, 30, String(o[k]), { size: 34, parent: c }); text(o.w - 300 + i * 150, 74, k, { size: 18, parent: c, color: 'rgba(255,255,255,.5)' });
    });
    const gw = (o.w - 56 - (o.cols - 1) * 8) / o.cols, gh = (o.h - 150 - (o.rows - 1) * 8) / o.rows;
    const cells = [];
    for (let r = 0; r < o.rows; r++) for (let q = 0; q < o.cols; q++) {
      const x = 28 + q * (gw + 8), y = 140 + r * (gh + 8);
      mk('div', '', Object.assign(box(x, y, gw, gh), { position: 'absolute', borderRadius: '8px', border: '1.5px dashed rgba(255,255,255,.18)' }), c);
      cells.push(thumb(x, y, gw, gh, r * o.cols + q, { parent: c, views: o.views ? o.views[r * o.cols + q] : null }));
    }
    return { el: c, cells, stats,
      post(i, t) { if (cells[i]) appear(cells[i], t, { y: 0, scale: .82, d: .45 }); },
      fill(a, b, t0, t1) { const n = b - a + 1; for (let i = 0; i < n; i++) this.post(a + i, t0 + (t1 - t0) * i / Math.max(1, n - 1)); },
      count(k, t, d, from, to, opt) { count(stats[k], t, d, from, to, opt); } };
  }
  // thumbnail grid / catalog with one highlighted
  function grid(o) {
    o = Object.assign({ x: 150, y: 300, cols: 4, rows: 3, cw: 180, ch: 160, gap: 16 }, o);
    const cells = [];
    for (let r = 0; r < o.rows; r++) for (let q = 0; q < o.cols; q++)
      cells.push(thumb(o.x + q * (o.cw + o.gap), o.y + r * (o.ch + o.gap), o.cw, o.ch, r * o.cols + q, { views: o.views ? o.views[r * o.cols + q] : null }));
    return { cells,
      fill(t, d = .9, from = 'start') { ft(cells, { autoAlpha: 0, scale: .85 }, { autoAlpha: 1, scale: 1, duration: .45, ease: 'back.out(1.3)', stagger: { amount: d, from } }, t); },
      highlight(i, t) { C.tl.to(cells.filter((_, j) => j !== i), { opacity: .28, duration: .35 }, t);
        C.tl.to(cells[i], { scale: 1.12, zIndex: 5, boxShadow: '0 0 0 5px #e8283c, 0 18px 40px rgba(0,0,0,.6)', duration: .4, ease: 'back.out(1.4)' }, t); } };
  }
  // streak calendar
  function calendar(o) {
    o = Object.assign({ x: 210, y: 320, cols: 7, rows: 4, cell: 82, gap: 12, title: 'Posting streak' }, o);
    const W = o.cols * (o.cell + o.gap) + 40, H = o.rows * (o.cell + o.gap) + 100;
    const c = card(o.x, o.y, W, H);
    text(24, 20, o.title, { size: 28, parent: c });
    const cells = [];
    for (let i = 0; i < o.cols * o.rows; i++) {
      const q = i % o.cols, r = Math.floor(i / o.cols);
      const b = mk('div', '', Object.assign(box(20 + q * (o.cell + o.gap), 76 + r * (o.cell + o.gap), o.cell, o.cell), { position: 'absolute', borderRadius: '14px', border: '1.5px solid rgba(255,255,255,.15)' }), c);
      cells.push(mk('div', 'r3-el', Object.assign(box(0, 0, o.cell, o.cell), { borderRadius: '13px', background: 'linear-gradient(135deg,#3dff8b,#10ac84)', boxShadow: '0 6px 14px rgba(0,0,0,.45)' }), b));
    }
    return { el: c, cells,
      check(i, t) { if (cells[i]) appear(cells[i], t, { y: 0, scale: .6, d: .35 }); },
      streak(a, b, t0, t1) { for (let i = a; i <= b; i++) this.check(i, t0 + (t1 - t0) * (i - a) / Math.max(1, b - a)); } };
  }
  // branch tree / pipeline: root -> children (nodes + connectors grow)
  function tree(o) {
    o = Object.assign({ x: 120, y: 520, root: 'Start', nodes: [] }, o);  // nodes: [{label, x, y, from}] from = index of parent (-1 = root)
    const rw = 240, rootEl = card(o.x, o.y - 40, rw, 80); text(0, 20, o.root, { size: 30, parent: rootEl, w: rw, align: 'center' });
    const els = [rootEl];
    o.nodes.forEach((n) => { const e = card(n.x, n.y - 36, n.w || 260, 72); text(0, 18, n.label, { size: 26, parent: e, w: n.w || 260, align: 'center' }); els.push(e); });
    return { root: rootEl, nodes: els.slice(1),
      grow(i, t) { const n = o.nodes[i], par = els[(n.from ?? -1) + 1]; connect(par, els[i + 1], t, { curve: .15 }); appear(els[i + 1], t + .3, { x: -20, y: 0 }); },
      focus(i, t) { C.tl.to(els[i + 1], { borderColor: 'rgba(232,40,60,.95)', duration: .3 }, t); pulse(els[i + 1], t); } };
  }
  // orbit of cards around a centre pill
  function orbit(o) {
    o = Object.assign({ cx: 540, cy: 560, r: 250, center: 'Topic', items: [], tw: 140, th: 180 }, o);
    const s = svgLayer(); svgEl('circle', { cx: o.cx, cy: o.cy, r: o.r, fill: 'none', stroke: 'rgba(255,255,255,.22)', 'stroke-width': 2.5, 'stroke-dasharray': '8 10' }, s);
    const pill = mk('div', 'r3-chip red r3-el', { left: px(o.cx), top: px(o.cy), transform: 'translate(-50%,-50%)', fontSize: '34px', padding: '14px 28px' }, null, o.center);
    const items = o.items.map((it, i) => {
      const a = -Math.PI / 2 + 2 * Math.PI * i / o.items.length, x = o.cx + o.r * Math.cos(a) - o.tw / 2, y = o.cy + o.r * Math.sin(a) * .9 - o.th / 2;
      const e = thumb(x, y, o.tw, o.th, i, { views: it.views }); if (it.label) chip(4, o.th - 40, it.label, null, { parent: e }).style.fontSize = '18px';
      return e;
    });
    return { pill, items, ring: s,
      add(i, t) { appear(items[i], t, { y: 0, scale: .7, d: .5 }); },
      focus(i, t) { C.tl.to(items.filter((_, j) => j !== i), { opacity: .3, duration: .35 }, t); C.tl.to(items[i], { scale: 1.18, duration: .45, ease: 'back.out(1.4)' }, t); } };
  }
  // chart: bars or line, building
  function chart(o) {
    o = Object.assign({ x: 150, y: 320, w: 780, h: 460, kind: 'bars', values: [20, 40, 70, 100], labels: [], title: '' }, o);
    const c = card(o.x, o.y, o.w, o.h);
    if (o.title) text(28, 22, o.title, { size: 28, parent: c });
    const n = o.values.length, bw = (o.w - 80) / n * .62, base = o.h - 60, top = 80;
    mk('div', '', Object.assign(box(30, base, o.w - 60, 3), { position: 'absolute', background: 'rgba(255,255,255,.3)' }), c);
    const bars = o.values.map((v, i) => {
      const x = 40 + i * (o.w - 80) / n + ((o.w - 80) / n - bw) / 2, h = (base - top) * v / Math.max(...o.values);
      const b = mk('div', 'r3-el', Object.assign(box(x, base - h, bw, h), { position: 'absolute', borderRadius: '10px 10px 0 0', transformOrigin: '50% 100%',
        background: i === n - 1 ? 'linear-gradient(180deg,#ff5a6a,#e8283c)' : 'linear-gradient(180deg,rgba(255,255,255,.9),rgba(255,255,255,.35))' }), c);
      if (o.labels[i]) text(x - 20, base + 12, o.labels[i], { size: 20, parent: c, w: bw + 40, align: 'center', color: 'rgba(255,255,255,.7)' });
      return b;
    });
    return { el: c, bars, bar(i, t) { ft(bars[i], { scaleY: 0 }, { scaleY: 1, duration: .6, ease: 'back.out(1.2)' }, t); } };
  }
  // numbered rows, unrevealed rows blurred
  function rows(o) {
    o = Object.assign({ x: 160, y: 320, w: 760, gap: 96, items: [] }, o);
    const els = o.items.map((it, i) => {
      const e = mk('div', 'r3-row r3-el', { left: px(o.x), top: px(o.y + i * o.gap), width: px(o.w) }, null, `<span class="n">${String(i + 1).padStart(2, '0')}</span><span class="t">${it}</span>`);
      lit(e, o.x, o.y + i * o.gap, o.w, 78, .7);
      return e;
    });
    const ts = els.map((e) => e.querySelector('.t'));
    return { els,
      show(t) { appear(els, t, { stagger: .06 }); ft(ts, { color: 'rgba(255,255,255,0)', textShadow: '0 0 14px rgba(255,255,255,.6)' }, { color: 'rgba(255,255,255,0)', duration: .01 }, t); },
      reveal(i, t) { ft(ts[i], { color: 'rgba(255,255,255,0)', textShadow: '0 0 14px rgba(255,255,255,.6)' }, { color: 'rgba(255,255,255,1)', textShadow: '0 0 0px rgba(255,255,255,0)', duration: .45 }, t);
        C.tl.to(els[i], { borderColor: 'rgba(255,90,106,.9)', duration: .3 }, t); if (i) C.tl.to(els[i - 1], { borderColor: 'rgba(255,255,255,.13)', duration: .3 }, t); } };
  }
  // network of avatars around a centre with a counter chip
  function network(o) {
    o = Object.assign({ cx: 540, cy: 560, r: 260, n: 8, center: '', value: 0 }, o);
    const hub = card(o.cx - 70, o.cy - 70, 140, 140, null, { borderRadius: '50%' });
    const nodes = [];
    for (let i = 0; i < o.n; i++) { const a = 2 * Math.PI * i / o.n - Math.PI / 2, rr = o.r * (.85 + .15 * ((i * 7) % 3) / 2);
      nodes.push(avatar(o.cx + rr * Math.cos(a) - 38, o.cy + rr * Math.sin(a) * .85 - 38, 76, i)); }
    const chipEl = chip(o.cx - 60, o.cy + 84, o.center || '0', null, { red: true });
    return { hub, nodes, chip: chipEl,
      link(i, t) { connect(hub, nodes[i], t, { curve: 0, color: 'rgba(255,255,255,.35)', w: 2 }); appear(nodes[i], t + .2, { y: 0, scale: .6, d: .4 }); },
      count(t, d, from, to, opt) { count(chipEl, t, d, from, to, opt); } };
  }
  // stacked pages that deal / fan
  function pages(o) {
    o = Object.assign({ x: 380, y: 320, w: 300, h: 400, n: 5 }, o);
    const els = [];
    for (let i = 0; i < o.n; i++) {
      const e = mk('div', 'r3-el', Object.assign(box(o.x, o.y, o.w, o.h), { position: 'absolute', background: '#f4f4f6', borderRadius: '8px', boxShadow: '0 18px 50px rgba(0,0,0,.6)' }));
      for (let j = 0; j < 10; j++) mk('div', '', Object.assign(box(24, 30 + j * 32, (o.w - 48) * (j ? .55 + .45 * ((j * 5) % 4) / 3 : .7), j ? 9 : 14), { position: 'absolute', borderRadius: '4px', background: j ? 'rgba(0,0,0,.2)' : '#e8283c' }), e);
      els.push(e);
    }
    return { els,
      deal(i, t) { ft(els[i], { autoAlpha: 0, y: 180, rotation: -12 }, { autoAlpha: 1, y: 0, rotation: (i - (o.n - 1) / 2) * 5, x: (i - (o.n - 1) / 2) * 70, duration: .6, ease: 'back.out(1.2)' }, t); } };
  }
  // offer / contract card with lines and a stamp
  function offer(o) {
    o = Object.assign({ x: 230, y: 300, w: 620, h: 520, title: 'Offer', lines: [], stamp: '' }, o);
    const c = card(o.x, o.y, o.w, o.h);
    text(32, 28, o.title, { size: 36, parent: c });
    const ls = o.lines.map((l, i) => text(32, 104 + i * 64, l, { size: 26, parent: c, color: 'rgba(255,255,255,.85)' }));
    const sig = svgEl('svg', { width: o.w, height: 120, style: `position:absolute;left:0;top:${o.h - 130}px;overflow:visible` }, c);
    const sp = svgEl('path', { d: `M40 80 C 120 20, 160 110, 230 60 S 330 30, 380 70`, fill: 'none', stroke: '#fff', 'stroke-width': 4, pathLength: 1, 'stroke-dasharray': 1, 'stroke-dashoffset': 1 }, sig);
    const st = o.stamp ? chip(o.w - 230, o.h - 110, o.stamp, null, { red: true, parent: c }) : null;
    return { el: c, lines: ls,
      line(i, t) { appear(ls[i], t, { x: -16, y: 0, d: .4 }); },
      sign(t) { draw(sp, t, .9); },
      stampIt(t) { if (st) ft(st, { autoAlpha: 0, scale: 1.8, rotation: -14 }, { autoAlpha: 1, scale: 1, rotation: -8, duration: .45, ease: 'back.out(1.6)' }, t); } };
  }

  // ---------------- camera rig ----------------
  function cam() {
    const el = C.camEl;
    return { el,
      push(t, d, s = 1.08, x = 0, y = 0) { C.tl.to(el, { scale: s, x, y, duration: d, ease: 'power2.inOut' }, t); },
      tilt(t, d, rx = 6, ry = -8) { C.tl.to(el, { rotationX: rx, rotationY: ry, transformPerspective: 1600, duration: d, ease: 'power2.inOut' }, t); },
      reset(t, d = .6) { C.tl.to(el, { scale: 1, x: 0, y: 0, rotationX: 0, rotationY: 0, duration: d, ease: 'power2.inOut' }, t); },
      // fly through a point (exit transition): origin at (px,py), scale up with motion blur
      through(t, d, x = 540, y = 560) { C.tl.set(el, { transformOrigin: `${x}px ${y}px` }, t); C.tl.to(el, { scale: 3.2, filter: 'blur(10px)', autoAlpha: 0, duration: d, ease: 'power3.in' }, t); } };
  }

  window.R3 = { TEMP, mk, box, ft, appear, leave, dim, pulse, draw, count, connect, chip, text, number, thumb, avatar, card, lit, light,
    doc, phone, profile, grid, calendar, tree, orbit, chart, rows, network, pages, offer, cam, svgLayer,
    begin(ctx) { C = ctx; C._svg = null; ctx.cam = cam(); return ctx; } };
})();
