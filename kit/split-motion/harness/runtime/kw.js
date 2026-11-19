/* ============================================================================
   kw.js — motion language for the split-motion harness (window.KW)  · v2
   STILLNESS IS THE DEFAULT. Things arrive with a soft eased settle (tiny overshoot),
   then HOLD. Continuous movement (slow push / parallax) only on hero beats.
   Fluidity comes from easing + timing quality, not from constant motion.

   Every helper: (tl, target, t, ...) with ABSOLUTE reel time t; deterministic.
   KW.scene(t0) marks the start of the current scene: every tween that starts later
   gets its FROM state applied at t0 (otherwise the element would show its FINAL state
   until its tween starts and then snap back = the "jump" bug of round 1).
   ============================================================================ */
(function () {
  const IR = { immediateRender: false };
  let T0 = 0;
  const q = (s) => (typeof s === 'string' ? document.querySelectorAll(s) : s);
  // fromTo with the FROM state guarded at scene start
  function ft(tl, el, from, to, t) {
    if (t > T0 + 1e-3) tl.set(el, from, T0);
    return tl.fromTo(el, from, Object.assign({}, to, IR), t);
  }
  // easing vocabulary: settles with a tiny overshoot, never bouncy
  const E = { settle: 'back.out(1.15)', soft: 'expo.out', glide: 'power3.out', calm: 'sine.inOut', out: 'power2.in' };
  const ENTER = {
    settle:  (tl, el, t, d = .62) => ft(tl, el, { autoAlpha: 0, y: 26, scale: .975 }, { autoAlpha: 1, y: 0, scale: 1, duration: d, ease: E.settle }, t),
    rise:    (tl, el, t, d = .6) => ft(tl, el, { autoAlpha: 0, y: 34 }, { autoAlpha: 1, y: 0, duration: d, ease: E.glide }, t),
    pop:     (tl, el, t, d = .52) => ft(tl, el, { autoAlpha: 0, scale: .82 }, { autoAlpha: 1, scale: 1, duration: d, ease: 'back.out(1.35)' }, t),
    focus:   (tl, el, t, d = .7) => ft(tl, el, { autoAlpha: 0, filter: 'blur(12px)', scale: 1.025 }, { autoAlpha: 1, filter: 'blur(0px)', scale: 1, duration: d, ease: E.soft }, t),
    bloom:   (tl, el, t, d = .8) => ft(tl, el, { autoAlpha: 0, scale: .94, filter: 'brightness(2.2) blur(6px)' }, { autoAlpha: 1, scale: 1, filter: 'brightness(1) blur(0px)', duration: d, ease: E.soft }, t),
    iris:    (tl, el, t, d = .7) => ft(tl, el, { autoAlpha: 1, clipPath: 'circle(0% at 50% 50%)' }, { clipPath: 'circle(75% at 50% 50%)', duration: d, ease: 'power2.inOut' }, t),
    wipe:    (tl, el, t, d = .6) => ft(tl, el, { autoAlpha: 1, clipPath: 'inset(0% 100% 0% 0%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: d, ease: 'power3.inOut' }, t),
    unfold:  (tl, el, t, d = .6) => ft(tl, el, { autoAlpha: 0, scaleY: .2, transformOrigin: '50% 0%' }, { autoAlpha: 1, scaleY: 1, duration: d, ease: E.soft }, t),
    tilt3d:  (tl, el, t, d = .8) => ft(tl, el, { autoAlpha: 0, rotationX: 24, y: 30, transformPerspective: 1400 }, { autoAlpha: 1, rotationX: 0, y: 0, duration: d, ease: E.settle }, t),
    flipY:   (tl, el, t, d = .75) => ft(tl, el, { autoAlpha: 0, rotationY: -40, transformPerspective: 1300 }, { autoAlpha: 1, rotationY: 0, duration: d, ease: E.settle }, t),
    zoomIn:  (tl, el, t, d = .75) => ft(tl, el, { autoAlpha: 0, scale: 1.18, filter: 'blur(8px)' }, { autoAlpha: 1, scale: 1, filter: 'blur(0px)', duration: d, ease: E.soft }, t),
    fall:    (tl, el, t, d = .7) => ft(tl, el, { autoAlpha: 0, y: -40 }, { autoAlpha: 1, y: 0, duration: d, ease: E.settle }, t),
  };
  // round-1 verbs kept as soft aliases (old plans still compile, but nothing slides across the frame)
  Object.assign(ENTER, { slideL: ENTER.settle, slideR: ENTER.settle, drop: ENTER.fall, swing: ENTER.tilt3d });
  const EXIT = {
    fade:     (tl, el, t, d = .32) => tl.to(el, { autoAlpha: 0, duration: d, ease: E.calm }, t),
    dissolve: (tl, el, t, d = .34) => tl.to(el, { autoAlpha: 0, filter: 'blur(8px)', duration: d, ease: E.out }, t),
    recede:   (tl, el, t, d = .32) => tl.to(el, { autoAlpha: 0, scale: .955, duration: d, ease: E.out }, t),
    lift:     (tl, el, t, d = .32) => tl.to(el, { autoAlpha: 0, y: -22, duration: d, ease: E.out }, t),
    irisOut:  (tl, el, t, d = .34) => tl.to(el, { clipPath: 'circle(0% at 50% 50%)', duration: d, ease: 'power2.in' }, t),
    collapse: (tl, el, t, d = .3) => tl.to(el, { autoAlpha: 0, scaleY: .3, duration: d, ease: E.out }, t),
  };
  Object.assign(EXIT, { blur: EXIT.dissolve, whipL: EXIT.recede, whipR: EXIT.recede, shrink: EXIT.recede,
                        pushUp: EXIT.lift, zoomPast: EXIT.dissolve, dropOut: EXIT.fade });
  // camera: none by default; slow continuous moves are for HERO beats only
  const CAMERA = {
    none:     (tl) => tl,
    push:     (tl, el, t0, t1) => ft(tl, el, { scale: 1 }, { scale: 1.045, duration: Math.max(.3, t1 - t0), ease: E.calm }, t0),
    pull:     (tl, el, t0, t1) => ft(tl, el, { scale: 1.045 }, { scale: 1, duration: Math.max(.3, t1 - t0), ease: E.calm }, t0),
    parallax: (tl, el, t0, t1) => {  // layers .px-far / .px-near move at different depths
      const d = Math.max(.3, t1 - t0);
      ft(tl, el, { scale: 1 }, { scale: 1.03, duration: d, ease: E.calm }, t0);
      ft(tl, el.replace(/c$/, '') + ' .px-far', { y: 10 }, { y: -10, duration: d, ease: E.calm }, t0);
      ft(tl, el.replace(/c$/, '') + ' .px-near', { y: -14 }, { y: 18, duration: d, ease: E.calm }, t0);
      return tl;
    },
    tilt:     (tl, el, t0, t1) => ft(tl, el, { rotationX: 5, rotationY: -4, transformPerspective: 1800 }, { rotationX: -2, rotationY: 4, duration: Math.max(.3, t1 - t0), ease: E.calm }, t0),
  };
  Object.assign(CAMERA, { driftL: CAMERA.none, driftR: CAMERA.none, rise: CAMERA.none, orbit: CAMERA.tilt });
  window.KW = {
    ENTER, EXIT, CAMERA, E, ft,
    scene(t0) { T0 = t0; },
    enter(tl, el, verb, t, d) { (ENTER[verb] || ENTER.settle)(tl, el, t, d); return tl; },
    exit(tl, el, verb, t, d) { (EXIT[verb] || EXIT.fade)(tl, el, t, d); tl.set(el, { autoAlpha: 0 }, t + (d || .36) + .02); return tl; },
    camera(tl, el, kind, t0, t1) { (CAMERA[kind] || CAMERA.none)(tl, el, t0, t1); return tl; },
    show(tl, el, t) { tl.set(el, { autoAlpha: 1 }, t); return tl; },
    hide(tl, el, t) { tl.set(el, { autoAlpha: 0 }, t); return tl; },
    // stroke draw via the SVG ATTRIBUTE: the CSS property gets auto-rounded to whole px by GSAP, and with
    // pathLength=1 that made every line jump 1px -> 0px in one frame (round-1 'zıplama')
    draw(tl, el, t, d = .7) { ft(tl, el, { attr: { 'stroke-dashoffset': 1 } }, { attr: { 'stroke-dashoffset': 0 }, duration: d, ease: 'power2.inOut' }, t); return tl; },
    grow(tl, el, t, d = .6, axis = 'scaleX') { ft(tl, el, { [axis]: 0 }, { [axis]: 1, duration: d, ease: E.settle }, t); return tl; },
    // highlight = a smooth state change (no class snapping)
    light(tl, el, t, on = true) {
      tl.to(el, on ? { borderColor: 'rgba(255,77,94,.95)', boxShadow: '0 0 34px rgba(232,40,60,.38)', duration: .35, ease: E.glide }
                   : { borderColor: 'rgba(255,255,255,.14)', boxShadow: '0 0 0 rgba(0,0,0,0)', duration: .35, ease: E.calm }, t);
      return tl;
    },
    unghost(tl, el, t) { ft(tl, el, { color: 'rgba(255,255,255,0)', textShadow: '0 0 14px rgba(255,255,255,.55)' },
                                 { color: 'rgba(255,255,255,1)', textShadow: '0 0 0px rgba(255,255,255,0)', duration: .45, ease: E.glide }, t); return tl; },
    // counters: tabular digits (no re-centering jitter); small integers do not count, they settle
    count(tl, sel, t, d, from, to, dec = 0, pre = '', suf = '') {
      const node = document.querySelector(sel); const p = { v: from };
      const fmt = (v) => pre + (dec ? v.toFixed(dec) : Math.round(v).toLocaleString('en-US')) + suf;
      if (!dec && Math.abs(to - from) <= 12) {
        tl.set(node, { textContent: fmt(to) }, T0);
        ft(tl, node, { autoAlpha: 0, scale: .9 }, { autoAlpha: 1, scale: 1, duration: .55, ease: 'back.out(1.3)' }, t);
        return tl;
      }
      tl.set(node, { textContent: fmt(from) }, T0);
      ft(tl, p, { v: from }, { v: to, duration: d, ease: 'power3.out', onUpdate: () => { node.textContent = fmt(p.v); } }, t);
      return tl;
    },
    typeWords(tl, sel, t, step = .09) {
      const ws = q(sel + ' .w');
      tl.set(sel, { autoAlpha: 1 }, t);
      ws.forEach((w, i) => tl.fromTo(w, { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: .42, ease: E.settle, ...IR }, t + i * step));
      tl.set(ws, { autoAlpha: 0 }, Math.max(0, t - .001));
      const u = document.querySelector(sel + ' .ul');
      if (u) { tl.set(u, { '--u': 0 }, Math.max(0, t - .001)); tl.fromTo(u, { '--u': 0 }, { '--u': 1, duration: .5, ease: 'power2.out', ...IR }, t + ws.length * step); }
      return tl;
    },
    cap(tl, el, t) { tl.fromTo(el, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: .14, ease: 'power2.out', ...IR }, t); return tl; },
    flash(tl, el, t, a = .45) { tl.fromTo(el, { opacity: a }, { opacity: 0, duration: .32, ease: 'power2.out', ...IR }, t); return tl; },
    // cinematic shine: one light sweep across the hero after it settles
    // the band travels from fully off-screen to fully off-screen and its opacity has an envelope:
    // switching it on/off with a band in view made the whole panel flash for a frame (round-2 detector find)
    shine(tl, el, t) {
      // band = 38-62 % of a 300 %-wide gradient: off-screen left at 95 %, off-screen right at 5 % -> travels
      // 1.8 panel widths (~46 px/frame). The first version crossed ~5 widths (~140 px/frame) = flicker.
      ft(tl, el, { backgroundPosition: '95% 0%' }, { backgroundPosition: '5% 0%', duration: 1.2, ease: 'sine.inOut' }, t);
      ft(tl, el, { opacity: 0 }, { opacity: 1, duration: .3, ease: 'sine.out' }, t);
      tl.to(el, { opacity: 0, duration: .3, ease: 'sine.in' }, t + .9);
      return tl;
    },
    // organic particles: one soft burst outward that decelerates into stillness
    burst(tl, sel, t) {
      q(sel).forEach((p) => {
        const dx = +p.dataset.dx, dy = +p.dataset.dy, dl = +p.dataset.dl;
        ft(tl, p, { x: 0, y: 0, autoAlpha: 0, scale: .4 }, { x: dx, y: dy, autoAlpha: +p.dataset.a, scale: 1, duration: 1.6, ease: 'expo.out' }, t + dl);
      });
      return tl;
    },
    glowIn(tl, el, t) { ft(tl, el, { autoAlpha: 0, scale: .7 }, { autoAlpha: 1, scale: 1, duration: 1.1, ease: E.soft }, t); return tl; },
  };
})();
