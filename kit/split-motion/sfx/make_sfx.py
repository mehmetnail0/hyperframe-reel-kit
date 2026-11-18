#!/usr/bin/env python3
"""Deterministic, license-free SFX for the split-motion style (pure Python, no deps).

usage: python3 -I kit/split-motion/sfx/make_sfx.py [OUTDIR]

Writes 48 kHz mono 16-bit WAVs:
  whoosh.wav      0.55 s  band-swept noise (chapter fly-ins, panel swaps)
  whoosh_big.wav  0.90 s  longer, lower sweep (punch-ins, recap)
  riser.wav       2.40 s  noise + rising tone swell, ends on the downbeat (fireworks)
  boom.wav        1.60 s  low thump + decaying crackle (the payoff hit)
  pop_soft.wav    0.12 s  rounded "pit" for object entrances
  tick.wav        0.05 s  tiny click for list items / counters

Prefer the user's own SFX library when it exists (e.g. sfxs/); these are the fallback.
Seeded LCG noise -> byte-identical output every run.
"""
import math, os, struct, sys, wave

SR = 48000
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


class Noise:
    def __init__(self, seed):
        self.s = seed

    def __call__(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x3FFFFFFF - 1.0


def svf_bandpass(x, f_of_t, q=0.9):
    low = band = 0.0
    out = []
    for i, v in enumerate(x):
        f = 2 * math.sin(math.pi * min(f_of_t(i / SR), SR / 6) / SR)
        high = v - low - q * band
        band += f * high
        low += f * band
        out.append(band)
    return out


def write(name, y, peak=0.9):
    m = max(1e-9, max(abs(v) for v in y))
    y = [v / m * peak for v in y]
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(v * 32767)) for v in y))
    print("wrote", name, round(len(y) / SR, 2), "s")


def env_swell(t, d, attack=0.55):
    p = t / d
    return (p / attack) ** 2 if p < attack else math.cos((p - attack) / (1 - attack) * math.pi / 2) ** 1.5


def whoosh(d, f0, f1, seed, name):
    n = Noise(seed); N = int(d * SR)
    x = [n() for _ in range(N)]
    y = svf_bandpass(x, lambda t: f0 * (f1 / f0) ** (t / d), q=0.7)
    y = [v * env_swell(i / SR, d, 0.6) for i, v in enumerate(y)]
    write(name, y, 0.8)


def riser(d=2.4):
    n = Noise(7); N = int(d * SR)
    x = [n() for _ in range(N)]
    y = svf_bandpass(x, lambda t: 300 * (5000 / 300) ** (t / d), q=0.5)
    ph = 0.0
    out = []
    for i, v in enumerate(y):
        t = i / SR
        f = 110 * (880 / 110) ** (t / d)
        ph += 2 * math.pi * f / SR
        e = (t / d) ** 2.2
        cut = 1.0 if t < d - 0.03 else max(0.0, (d - t) / 0.03)
        out.append((0.7 * v + 0.35 * math.sin(ph) + 0.15 * math.sin(2 * ph)) * e * cut)
    write("riser.wav", out, 0.85)


def boom(d=1.6):
    n = Noise(99); N = int(d * SR)
    out = []
    ph = 0.0
    crack_env = 0.0
    for i in range(N):
        t = i / SR
        f = 38 + 90 * math.exp(-t * 18)
        ph += 2 * math.pi * f / SR
        thump = math.sin(ph) * math.exp(-t * 4.5)
        # sparse crackle bursts (fireworks sparkle), deterministic
        if i % 1700 == 0:
            crack_env = 0.6 + 0.4 * abs(n())
        crack_env *= 0.9992
        crackle = n() * crack_env * math.exp(-t * 2.2) * (0.25 if t > 0.08 else 0.0)
        out.append(0.9 * thump + crackle)
    write("boom.wav", out, 0.9)


def pop_soft(d=0.12):
    N = int(d * SR); out = []; ph = 0.0
    for i in range(N):
        t = i / SR
        f = 1400 * math.exp(-t * 30) + 520
        ph += 2 * math.pi * f / SR
        out.append(math.sin(ph) * math.exp(-t * 45) * min(1, t / 0.002))
    write("pop_soft.wav", out, 0.7)


def tick(d=0.05):
    n = Noise(3); N = int(d * SR)
    x = [n() * math.exp(-i / SR * 160) for i in range(N)]
    write("tick.wav", svf_bandpass(x, lambda t: 3200, q=0.4), 0.6)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    whoosh(0.55, 500, 4200, 11, "whoosh.wav")
    whoosh(0.90, 240, 2600, 23, "whoosh_big.wav")
    riser(); boom(); pop_soft(); tick()
