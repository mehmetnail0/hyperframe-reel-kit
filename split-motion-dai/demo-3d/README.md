# demo-3d — split-motion "3D mode" (7 s, separate from the reel)

Two hero objects from `split-motion-dai` rebuilt as real 3D inside HyperFrames:
the chapter **ring** as a glossy glass neon tube (clear-coated transparent torus over an emissive
core, orbiting light beads, the camera flies through it) and the **phone** with the follower
counter (glass slab, live canvas-texture screen, metallic gold coins), with `RoomEnvironment`
reflections, coloured point lights and UnrealBloom.

* three.js r181 self-hosted in `assets/vendor/three/` (MIT, `LICENSE`), import map + module script.
* Deterministic: `frame(t)` is a pure function of t, driven by one GSAP tween (no clock, no rAF).
* `demo.mp4` 1080×1920 30 fps · `compare.jpg` flat (reel) vs 3D (demo).
* Render here: CPU only (SwiftShader, HyperFrames reports "WebGL unavailable → software"):
  **178 s for 210 frames, 4 workers** (~3.4 s/frame/worker).

```bash
npm run check && npm run render -- -o demo.mp4 -w $(nproc)
```
