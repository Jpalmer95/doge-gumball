"""Procedural retro sound-effect generator (jsfxr-style).

Zero API cost, fully offline, fully deterministic from the model seed, and
the output is original synthesized audio — no model license involved, so the
machine dedicates every SFX as CC0 without any caveat.

Archetypes (seeded, not chosen by hand):
  * blip / coin  — short square-wave with fast pitch drop
  * powerup      — rising square sweep
  * explosion    — decaying noise burst
  * laser        — descending saw sweep
  * jump/boing   — sine with pitch bounce
  * fanfare      — little 4-note arpeggio
  * select       — two-tone tick
"""
import math
import random
import struct
import wave
from pathlib import Path

from .base import Generator, GenerationResult

SAMPLE_RATE = 22050


class SfxGenerator(Generator):
    name = "game_sfx"
    requires_network = False
    live = False  # procedural — always available, not a "live" model call

    def generate(self, prompt: str, model_seed: int, out_dir: str) -> GenerationResult:
        rng = random.Random(model_seed)
        archetype = rng.choice(
            ["blip", "powerup", "explosion", "laser", "boing", "fanfare", "select"]
        )
        samples = self._render(rng, archetype)
        path = self._out_path(out_dir, f"sfx_{model_seed}", "wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(b"".join(
                struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
                for s in samples
            ))
        return GenerationResult(
            path=path, mime="audio/wav",
            size_bytes=Path(path).stat().st_size,
            license="CC0-1.0", model="procedural/jsfxr-style",
            extra={"archetype": archetype, "prompt": prompt},
        )

    # -- synthesis ---------------------------------------------------------
    def _render(self, rng: random.Random, archetype: str) -> list[float]:
        if archetype == "blip":
            return self._square(rng, dur=0.25, f0=880, f1=180, decay=14)
        if archetype == "powerup":
            return self._square(rng, dur=0.45, f0=220, f1=1320, decay=10, vibrato=6)
        if archetype == "explosion":
            return self._noise(rng, dur=0.7, decay=9, lowpass=True)
        if archetype == "laser":
            return self._saw(rng, dur=0.4, f0=1400, f1=140, decay=10)
        if archetype == "boing":
            return self._boing(rng, dur=0.5, f0=180)
        if archetype == "fanfare":
            return self._arp(rng, dur=0.9, base=440)
        return self._select(rng)

    def _env(self, n: int, dur: float, decay: float) -> list[float]:
        """Exponential decay envelope."""
        t = [i / SAMPLE_RATE for i in range(n)]
        return [math.exp(-decay * ti / dur) for ti in t]

    def _square(self, rng, dur, f0, f1, decay, vibrato=0.0):
        n = int(SAMPLE_RATE * dur)
        env = self._env(n, dur, decay)
        out = []
        phase = 0.0
        for i in range(n):
            t = i / SAMPLE_RATE
            f = f0 + (f1 - f0) * (i / n)
            if vibrato:
                f *= 1.0 + 0.5 * vibrato * math.sin(2 * math.pi * 6 * t) / 100.0
            phase += f / SAMPLE_RATE
            out.append((1.0 if (phase % 1.0) < 0.5 else -1.0) * env[i])
        return out

    def _saw(self, rng, dur, f0, f1, decay):
        n = int(SAMPLE_RATE * dur)
        env = self._env(n, dur, decay)
        out = []
        phase = 0.0
        for i in range(n):
            f = f0 + (f1 - f0) * (i / n)
            phase += f / SAMPLE_RATE
            out.append((2 * (phase % 1.0) - 1.0) * env[i])
        return out

    def _noise(self, rng, dur, decay, lowpass=True):
        n = int(SAMPLE_RATE * dur)
        env = self._env(n, dur, decay)
        prev = 0.0
        out = []
        for i in range(n):
            white = rng.uniform(-1, 1)
            if lowpass:  # crude one-pole lowpass -> "explosion" body
                prev = prev + 0.25 * (white - prev)
                white = prev
            out.append(white * env[i])
        return out

    def _boing(self, rng, dur, f0):
        n = int(SAMPLE_RATE * dur)
        env = self._env(n, dur, 8)
        out = []
        phase = 0.0
        for i in range(n):
            t = i / SAMPLE_RATE
            bounce = max(0.0, math.sin(math.pi * min(1.0, t / dur)))  # 0->1->0
            f = f0 * (1.0 + 0.9 * bounce)
            phase += f / SAMPLE_RATE
            out.append(math.sin(2 * math.pi * phase) * env[i])
        return out

    def _arp(self, rng, dur, base):
        notes = [base * m for m in (1.0, 1.25, 1.5, 2.0, 1.5, 2.0, 2.5, 3.0)]
        seg = dur / len(notes)
        out = []
        for fi, f in enumerate(notes):
            n = int(SAMPLE_RATE * seg)
            phase = 0.0
            for i in range(n):
                phase += f / SAMPLE_RATE
                amp = math.sin(math.pi * i / n)  # per-note fade in/out
                out.append(math.sin(2 * math.pi * phase) * 0.8 * amp)
        return out

    def _select(self, rng):
        out = []
        for f, d in ((660, 0.06), (990, 0.09)):
            n = int(SAMPLE_RATE * d)
            phase = 0.0
            for i in range(n):
                phase += f / SAMPLE_RATE
                amp = math.sin(math.pi * i / n)
                out.append(math.sin(2 * math.pi * phase) * amp)
        return out
