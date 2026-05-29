/* ============================================================================
   KIT: anim.js  —  Reusable GSAP timeline helpers  (window.HFKit)
   COPY-PASTE source of truth. Optional SUGAR over hand-written tweens: a
   composition can call HFKit.captionIn(tl,'#cap',3.2) instead of writing the
   from-tween by hand. Compositions are free to ignore this and hand-author
   every tween — nothing here is required.

   • Dependency-free: assumes the global `gsap` is already loaded.
   • DETERMINISTIC ONLY — no Math.random, no Date.now, no network. Every call
     with the same args produces the exact same timeline (required for
     HyperFrames seek/render to stay frame-stable).
   • Every helper takes (tl, sel, t): a paused gsap timeline, a selector/element,
     and an absolute time `t` (seconds) to anchor the tween at.

   Each helper RETURNS `tl` so calls can chain:
     HFKit.captionIn(HFKit.drawStroke(tl,'#bar',0), '#cap', .3);

   NOTE on exits: captionIn provides only the IN. The matching auto-OUT
   (~0.12s before the clip ends) is the COMPOSITION's job — it knows the clip's
   data-duration; this kit does not.
   ============================================================================ */

window.HFKit = window.HFKit || {

  /* Quick caption pop-in. Settles with a soft back-overshoot. IN only. */
  captionIn(tl, sel, t) {
    tl.fromTo(sel,
      { y: 18, opacity: 0, scale: .96 },
      { y: 0, opacity: 1, scale: 1, duration: .22, ease: 'back.out(1.5)' }, t);
    return tl;
  },

  /* Reveal a pre-hidden stroke path (dasharray==dashoffset) by drawing it. */
  drawStroke(tl, sel, t, dur = .6) {
    tl.to(sel, { strokeDashoffset: 0, duration: dur, ease: 'power2.inOut' }, t);
    return tl;
  },

  /* Punch in then settle back to 1 — mirrors the proven [[t,d,s]] pulse. */
  zoomPulse(tl, sel, t, s = 1.08, d = .28) {
    tl.to(sel, { scale: s, duration: d, ease: 'power2.out' }, t);
    tl.to(sel, { scale: 1, duration: d * 2, ease: 'power2.inOut' }, t + d);
    return tl;
  },

  /* Directional whip entrance: slides in from left/right and snaps to place. */
  whipIn(tl, sel, t, dir = 'left') {
    const fromX = dir === 'right' ? 200 : -200;
    tl.from(sel, { x: fromX, opacity: 0, duration: .35, ease: 'power3.out' }, t);
    return tl;
  },

  /* Full-bg cut: punch the scene IN at t and back OUT at t+dur. */
  fullBgPunch(tl, sel, t, dur) {
    tl.fromTo(sel, { opacity: 0, scale: 1.04 },
      { opacity: 1, scale: 1, duration: .14, ease: 'power2.out' }, t);
    tl.to(sel, { opacity: 0, scale: 1.08, duration: .35, ease: 'power2.in' }, t + dur);
    return tl;
  },

  /* Generic exit: scale up slightly + fade out. */
  sceneOut(tl, sel, t) {
    tl.to(sel, { scale: 1.06, opacity: 0, duration: .35, ease: 'power2.in' }, t);
    return tl;
  },
};
