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


MOODS = {
    # name: (chord progression as MIDI triads, seconds per chord, arpeggio notes per chord, pluck level)
    "calm":   ([[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], 2.0, 4, 0.18),   # Am F C G, lo-fi
    "upbeat": ([[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]], 1.0, 4, 0.24),   # C G Am F, faster
    "dark":   ([[50, 53, 57], [46, 50, 53], [48, 52, 55], [45, 49, 52]], 2.0, 2, 0.14),   # Dm Bb C A, tense
}


def track(seconds, seed=0, mood="calm"):
    prog, step, notes, pl = MOODS[mood]
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    out = np.zeros(n + SR * 3)
    i, pos = 0, 0
    while pos < n:
        ch = prog[i % len(prog)]
        pad = _pad([_note(m - 12) for m in ch] + [_note(ch[0] - 24)], step + 0.8)
        out[pos:pos + len(pad)] += 0.55 * pad
        for k in range(notes):  # arpeggio spread evenly over the chord
            m = ch[(k + rng.integers(0, 2)) % 3] + 12
            p = _pluck(_note(m), 0.9)
            a = pos + int(SR * k * step / notes)
            out[a:a + len(p)] += pl * p
        pos += int(SR * step); i += 1
    out = out[:n]
    # gentle low-pass (moving average) and fades
    k = 6
    out = np.convolve(out, np.ones(k) / k, mode="same")
    fade = int(SR * 1.5)
    out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return (out / (np.abs(out).max() + 1e-9)).astype("float32")
