/* ============================================================================
   kw.js — motion VERBS for the split-motion harness (window.KW)
   Every helper: (tl, target, t, opts) with ABSOLUTE reel time t; deterministic.
   The scene compiler (harness/scenes.py) only emits calls to these, so a new
   verb added here is instantly available to every planner/model.
   All fromTo use immediateRender:false (a late fromTo must not paint at t=0).
   ============================================================================ */
(function () {
  const IR = { immediateRender: false };
  const q = (s) => (typeof s === 'string' ? document.querySelectorAll(s) : s);
  const ENTER = {
    rise:    (tl, el, t, d = .42) => tl.fromTo(el, { autoAlpha: 0, y: 70, filter: 'blur(6px)' }, { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: d, ease: 'power3.out', ...IR }, t),
    pop:     (tl, el, t, d = .38) => tl.fromTo(el, { autoAlpha: 0, scale: .55 }, { autoAlpha: 1, scale: 1, duration: d, ease: 'back.out(1.8)', ...IR }, t),
    slideL:  (tl, el, t, d = .45) => tl.fromTo(el, { autoAlpha: 0, x: 420 }, { autoAlpha: 1, x: 0, duration: d, ease: 'expo.out', ...IR }, t),
    slideR:  (tl, el, t, d = .45) => tl.fromTo(el, { autoAlpha: 0, x: -420 }, { autoAlpha: 1, x: 0, duration: d, ease: 'expo.out', ...IR }, t),
    drop:    (tl, el, t, d = .55) => tl.fromTo(el, { autoAlpha: 0, y: -380 }, { autoAlpha: 1, y: 0, duration: d, ease: 'bounce.out', ...IR }, t),
    flipY:   (tl, el, t, d = .55) => tl.fromTo(el, { autoAlpha: 0, rotationY: -82, transformPerspective: 1200 }, { autoAlpha: 1, rotationY: 0, duration: d, ease: 'power3.out', ...IR }, t),
    tilt3d:  (tl, el, t, d = .6) => tl.fromTo(el, { autoAlpha: 0, rotationX: 58, y: 120, transformPerspective: 1300 }, { autoAlpha: 1, rotationX: 0, y: 0, duration: d, ease: 'power3.out', ...IR }, t),
    iris:    (tl, el, t, d = .5) => tl.fromTo(el, { autoAlpha: 1, clipPath: 'circle(0% at 50% 50%)' }, { clipPath: 'circle(75% at 50% 50%)', duration: d, ease: 'power2.inOut', ...IR }, t),
    wipe:    (tl, el, t, d = .45) => tl.fromTo(el, { autoAlpha: 1, clipPath: 'inset(0% 100% 0% 0%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: d, ease: 'power3.inOut', ...IR }, t),
    unfold:  (tl, el, t, d = .45) => tl.fromTo(el, { autoAlpha: 0, scaleY: .05, transformOrigin: '50% 0%' }, { autoAlpha: 1, scaleY: 1, duration: d, ease: 'expo.out', ...IR }, t),
    zoomIn:  (tl, el, t, d = .5) => tl.fromTo(el, { autoAlpha: 0, scale: 1.7, filter: 'blur(10px)' }, { autoAlpha: 1, scale: 1, filter: 'blur(0px)', duration: d, ease: 'power3.out', ...IR }, t),
    swing:   (tl, el, t, d = .7) => tl.fromTo(el, { autoAlpha: 0, rotation: -14, y: 40, transformOrigin: '50% 0%' }, { autoAlpha: 1, rotation: 0, y: 0, duration: d, ease: 'elastic.out(1,.55)', ...IR }, t),
    focus:   (tl, el, t, d = .55) => tl.fromTo(el, { autoAlpha: 0, filter: 'blur(18px)', scale: 1.05 }, { autoAlpha: 1, filter: 'blur(0px)', scale: 1, duration: d, ease: 'power2.out', ...IR }, t),
  };
  const EXIT = {
    fade:    (tl, el, t, d = .22) => tl.to(el, { autoAlpha: 0, duration: d, ease: 'power1.in' }, t),
    blur:    (tl, el, t, d = .25) => tl.to(el, { autoAlpha: 0, filter: 'blur(10px)', scale: 1.06, duration: d, ease: 'power2.in' }, t),
    whipL:   (tl, el, t, d = .26) => tl.to(el, { autoAlpha: 0, x: -560, duration: d, ease: 'power3.in' }, t),
    whipR:   (tl, el, t, d = .26) => tl.to(el, { autoAlpha: 0, x: 560, duration: d, ease: 'power3.in' }, t),
    shrink:  (tl, el, t, d = .25) => tl.to(el, { autoAlpha: 0, scale: .4, duration: d, ease: 'back.in(1.6)' }, t),
    pushUp:  (tl, el, t, d = .3) => tl.to(el, { autoAlpha: 0, y: -260, duration: d, ease: 'power3.in' }, t),
    zoomPast:(tl, el, t, d = .3) => tl.to(el, { autoAlpha: 0, scale: 2.6, duration: d, ease: 'power2.in' }, t),
    collapse:(tl, el, t, d = .25) => tl.to(el, { autoAlpha: 0, scaleY: .02, duration: d, ease: 'power3.in' }, t),
    irisOut: (tl, el, t, d = .3) => tl.to(el, { clipPath: 'circle(0% at 50% 50%)', duration: d, ease: 'power2.in' }, t),
    dropOut: (tl, el, t, d = .32) => tl.to(el, { autoAlpha: 0, y: 420, rotation: 6, duration: d, ease: 'power2.in' }, t),
  };
  const CAMERA = {
    push:     (tl, el, t0, t1) => tl.fromTo(el, { scale: 1 }, { scale: 1.07, duration: Math.max(.2, t1 - t0), ease: 'none', ...IR }, t0),
    pull:     (tl, el, t0, t1) => tl.fromTo(el, { scale: 1.08 }, { scale: 1, duration: Math.max(.2, t1 - t0), ease: 'none', ...IR }, t0),
    driftL:   (tl, el, t0, t1) => tl.fromTo(el, { x: 26 }, { x: -26, duration: Math.max(.2, t1 - t0), ease: 'none', ...IR }, t0),
    driftR:   (tl, el, t0, t1) => tl.fromTo(el, { x: -26 }, { x: 26, duration: Math.max(.2, t1 - t0), ease: 'none', ...IR }, t0),
    rise:     (tl, el, t0, t1) => tl.fromTo(el, { y: 24 }, { y: -24, duration: Math.max(.2, t1 - t0), ease: 'none', ...IR }, t0),
    tilt:     (tl, el, t0, t1) => tl.fromTo(el, { rotationX: 10, rotationY: -8, transformPerspective: 1600 }, { rotationX: -4, rotationY: 8, duration: Math.max(.2, t1 - t0), ease: 'sine.inOut', ...IR }, t0),
    orbit:    (tl, el, t0, t1) => tl.fromTo(el, { rotationY: -12, transformPerspective: 1500 }, { rotationY: 12, duration: Math.max(.2, t1 - t0), ease: 'sine.inOut', ...IR }, t0),
    none:     (tl) => tl,
  };
  window.KW = {
    ENTER, EXIT, CAMERA,
    enter(tl, el, verb, t, d) { (ENTER[verb] || ENTER.rise)(tl, el, t, d); return tl; },
    exit(tl, el, verb, t, d) { (EXIT[verb] || EXIT.fade)(tl, el, t, d); tl.set(el, { autoAlpha: 0 }, t + (d || .35) + .02); return tl; },
    camera(tl, el, kind, t0, t1) { (CAMERA[kind] || CAMERA.none)(tl, el, t0, t1); return tl; },
    show(tl, el, t) { tl.set(el, { autoAlpha: 1 }, t); return tl; },
    hide(tl, el, t) { tl.set(el, { autoAlpha: 0 }, t); return tl; },
    draw(tl, el, t, d = .5) { tl.fromTo(el, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: d, ease: 'power2.inOut', ...IR }, t); return tl; },
    grow(tl, el, t, d = .45, axis = 'scaleX') { tl.fromTo(el, { [axis]: 0 }, { [axis]: 1, duration: d, ease: 'power3.out', ...IR }, t); return tl; },
    pulse(tl, el, t) { tl.fromTo(el, { scale: 1 }, { scale: 1.08, duration: .12, yoyo: true, repeat: 1, ease: 'power1.inOut', ...IR }, t); return tl; },
    count(tl, sel, t, d, from, to, dec = 0, pre = '', suf = '') {
      const node = document.querySelector(sel); const p = { v: from };
      tl.fromTo(p, { v: from }, { v: to, duration: d, ease: 'power2.out', ...IR,
        onUpdate: () => { node.textContent = pre + (dec ? p.v.toFixed(dec) : Math.round(p.v).toLocaleString('en-US')) + suf; } }, t);
      return tl;
    },
    typeWords(tl, sel, t, step = .09) {
      const ws = q(sel + ' .w');
      tl.set(sel, { autoAlpha: 1 }, t);
      ws.forEach((w, i) => tl.fromTo(w, { autoAlpha: 0, y: 26 }, { autoAlpha: 1, y: 0, duration: .26, ease: 'power3.out', ...IR }, t + i * step));
      const u = document.querySelector(sel + ' .ul');
      if (u) tl.fromTo(u, { '--u': 0 }, { '--u': 1, duration: .35, ease: 'power2.out', ...IR }, t + ws.length * step);
      return tl;
    },
    cap(tl, el, t, style) {
      if (style === 'slam') tl.fromTo(el, { scale: 1.35, opacity: 0 }, { scale: 1, opacity: 1, duration: .12, ease: 'power3.out', ...IR }, t);
      else tl.fromTo(el, { scale: .86, y: 8, opacity: 0 }, { scale: 1, y: 0, opacity: 1, duration: .1, ease: 'back.out(2.4)', ...IR }, t);
      return tl;
    },
    flash(tl, el, t, a = .55) { tl.fromTo(el, { opacity: a }, { opacity: 0, duration: .24, ease: 'power2.out', ...IR }, t); return tl; },
  };
})();
