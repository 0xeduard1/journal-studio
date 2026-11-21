"""Original background music, generated in code (no samples, no copyright): a calm lo-fi pad + soft arpeggio."""
import numpy as np

SR = 24000


def _note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _pad(freqs, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.8)
    s = sum(np.sin(2 * np.pi * f * d * t) for f in freqs for d in (0.997, 1.003)) / (2 * len(freqs))
    return s * env


def _pluck(f, dur):
    t = np.arange(int(SR * dur)) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return s * np.exp(-t * 6)


def track(seconds, seed=0):
    # Am - F - C - G, 2 s per chord (60 bpm feel)
    prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    out = np.zeros(n + SR * 3)
    step, i, pos = 2.0, 0, 0
    while pos < n:
        ch = prog[i % len(prog)]
        pad = _pad([_note(m - 12) for m in ch] + [_note(ch[0] - 24)], step + 0.8)
        out[pos:pos + len(pad)] += 0.55 * pad
        for k in range(4):  # arpeggio, one note every half second
            m = ch[(k + rng.integers(0, 2)) % 3] + 12
            p = _pluck(_note(m), 0.9)
            a = pos + int(SR * k * 0.5)
            out[a:a + len(p)] += 0.18 * p
        pos += int(SR * step); i += 1
    out = out[:n]
    # gentle low-pass (moving average) and fades
    k = 6
    out = np.convolve(out, np.ones(k) / k, mode="same")
    fade = int(SR * 1.5)
    out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return (out / (np.abs(out).max() + 1e-9)).astype("float32")
