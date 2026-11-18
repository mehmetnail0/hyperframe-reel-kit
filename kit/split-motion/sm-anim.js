/* ============================================================================
   KIT: sm-anim.js — GSAP helpers for the split-motion style  (window.SMKit)
   Same contract as kit/anim.js: every helper takes (tl, sel, t, ...) with an
   absolute time t in seconds, returns tl, and is DETERMINISTIC (no random, no
   Date). Needs the global `gsap`.
   ============================================================================ */
window.SMKit = window.SMKit || {

  /* Hero object life: scale-up + blur-in (~0.3 s), slow drift, scale/blur out.
     t0 = enter, t1 = exit start. dir = drift direction (+1 up, -1 down). */
  hero(tl, sel, t0, t1, o = {}) {
    const fromS = o.fromScale ?? .55, drift = o.drift ?? 18, dir = o.dir ?? 1;
    tl.fromTo(sel, { autoAlpha: 0, scale: fromS, filter: 'blur(14px)', y: 30 * dir },
      { autoAlpha: 1, scale: 1, filter: 'blur(0px)', y: 0, duration: .32, ease: 'back.out(1.6)' }, t0);
    // slow drift for the whole life — never a static panel
    tl.to(sel, { y: -drift * dir, scale: 1 + (o.grow ?? .045), duration: Math.max(.2, t1 - t0 - .32),
      ease: 'none' }, t0 + .32);
    if (!o.keep) {
      tl.to(sel, { autoAlpha: 0, scale: (o.outScale ?? 1.18), filter: 'blur(10px)',
        duration: .24, ease: 'power2.in' }, t1);
      tl.set(sel, { autoAlpha: 0, scale: 1, y: 0, filter: 'none' }, t1 + .26);  // hard kill
    }
    return tl;
  },

  /* Swap: whip a hero out to the side (for "next item" beats). */
  whipOut(tl, sel, t, dir = -1) {
    tl.to(sel, { x: 520 * dir, autoAlpha: 0, filter: 'blur(12px)', duration: .26, ease: 'power3.in' }, t);
    return tl;
  },

  /* Pop a child element (chip, icon, coin row) in. */
  pop(tl, sel, t, o = {}) {
    tl.fromTo(sel, { autoAlpha: 0, scale: o.from ?? .4, y: o.y ?? 16, filter: 'blur(6px)' },
      { autoAlpha: 1, scale: 1, y: 0, filter: 'blur(0px)', duration: o.d ?? .26, ease: 'back.out(2)' }, t);
    return tl;
  },

  /* Draw an SVG path that has pathLength="1" (.sm-line or any stroke). */
  draw(tl, sel, t, dur = .5, ease = 'power2.inOut') {
    tl.fromTo(sel, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: dur, ease }, t);
    return tl;
  },

  /* Header types on word by word. sel = header element containing .w spans. */
  typeHeader(tl, sel, t, step = .14) {
    const words = gsap.utils.toArray(sel + ' .w');
    tl.set(sel, { autoAlpha: 1 }, t);
    words.forEach((w, i) => {
      tl.fromTo(w, { autoAlpha: 0, y: 22, filter: 'blur(8px)' },
        { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: .22, ease: 'power2.out' }, t + i * step);
    });
    const acc = document.querySelector(sel + ' .acc');
    if (acc) tl.fromTo(acc, { '--ul': 0 }, { '--ul': 1, duration: .35, ease: 'power2.out' }, t + words.length * step);
    return tl;
  },
  headerOut(tl, sel, t) {
    tl.to(sel, { autoAlpha: 0, y: -18, filter: 'blur(8px)', duration: .2, ease: 'power2.in' }, t);
    return tl;
  },

  /* Chapter fly-in: the recurring device fills the panel, the camera flies INTO
     it (overshoots off-frame) while the big number + label punch in.
     device = the device element, chap = .sm-chap element. Total ~1.3 s. */
  chapter(tl, device, chap, t, dur = 1.3) {
    tl.fromTo(device, { autoAlpha: 0, scale: .35, rotate: -25, filter: 'blur(10px)' },
      { autoAlpha: 1, scale: 1.25, rotate: 0, filter: 'blur(0px)', duration: .3, ease: 'power3.out' }, t);
    tl.to(device, { scale: 3.2, rotate: 18, duration: dur - .55, ease: 'power1.in' }, t + .3);
    tl.to(device, { scale: 9, autoAlpha: 0, filter: 'blur(18px)', duration: .25, ease: 'power3.in' }, t + dur - .25);
    tl.fromTo(chap, { autoAlpha: 0, scale: 1.6, filter: 'blur(14px)' },
      { autoAlpha: 1, scale: 1, filter: 'blur(0px)', duration: .22, ease: 'power3.out' }, t + .18);
    tl.to(chap, { scale: 1.06, duration: dur - .6, ease: 'none' }, t + .4);
    tl.to(chap, { autoAlpha: 0, scale: .8, filter: 'blur(10px)', duration: .2, ease: 'power2.in' }, t + dur - .2);
    return tl;
  },

  /* Number counter (deterministic): writes into el.textContent. */
  counter(tl, el, t, dur, from, to, fmt = (v) => Math.round(v).toLocaleString('en-US'), ease = 'power1.in') {
    const node = typeof el === 'string' ? document.querySelector(el) : el;
    const p = { v: from };
    tl.fromTo(p, { v: from }, { v: to, duration: dur, ease, onUpdate: () => { node.textContent = fmt(p.v); } }, t);
    return tl;
  },

  /* Seam caption word pop (the clip itself handles visibility). */
  word(tl, sel, t) {
    tl.fromTo(sel, { scale: .82, y: 10, opacity: .0 }, { scale: 1, y: 0, opacity: 1, duration: .1, ease: 'back.out(2.5)' }, t);
    return tl;
  },

  /* Full-screen punch-in: hide the panel layer(s), punch the video scale, flash. */
  punch(tl, layers, vid, flash, t0, t1) {
    // NOTE immediateRender:false everywhere — a fromTo placed later in the
    // timeline would otherwise paint its FROM state at t=0 (hidden panel,
    // grey veil, zoomed video before the first punch).
    const IR = { immediateRender: false };
    tl.set(layers, { autoAlpha: 0 }, t0);
    tl.fromTo(vid, { scale: 1.12 }, { scale: 1, duration: .45, ease: 'power3.out', ...IR }, t0);
    tl.to(vid, { scale: 1.035, duration: Math.max(.1, t1 - t0 - .45), ease: 'none' }, t0 + .45);
    if (flash) tl.fromTo(flash, { opacity: .55 }, { opacity: 0, duration: .22, ease: 'power2.out', ...IR }, t0);
    tl.set(vid, { scale: 1 }, t1);
    tl.fromTo(layers, { autoAlpha: 0, y: -40 }, { autoAlpha: 1, y: 0, duration: .28, ease: 'power3.out', ...IR }, t1);
    if (flash) tl.fromTo(flash, { opacity: .18 }, { opacity: 0, duration: .16, ease: 'power2.out', ...IR }, t1);
    return tl;
  },
};
