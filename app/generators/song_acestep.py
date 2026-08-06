"""Song generation via the official ACE-Step Space (Apache-2.0 model).

/__call__ signature verified 2026-08-06 (22 params). The machine maps its
drawn prompt -> tags and pins the model seed via `manual_seeds` so songs are
reproducible (fairness: same tx -> same seed -> same song). Empty lyrics =
instrumental.

Cost: 0 USD (ZeroGPU quota). Slow: expect 1-3 minutes for a full track.
"""
import os
import shutil
from pathlib import Path

from gradio_client import Client, handle_file  # noqa: E402

from .base import Generator, GenerationResult, resolve_token

SPACE = "ACE-Step/ACE-Step"


class AceStepSongGenerator(Generator):
    name = "song_acestep"
    requires_network = True
    live = True

    def generate(self, prompt: str, model_seed: int, out_dir: str) -> GenerationResult:
        token = resolve_token()
        if not token:
            raise RuntimeError("HF_TOKEN not set — required for ZeroGPU Space quota")

        client = Client(SPACE, token=token, verbose=False)

        result = client.predict(
            audio_duration=30.0,
            prompt=prompt,          # "Tags" field — the machine's drawn prompt
            lyrics="",              # instrumental by default (blind draws)
            infer_step=50,          # INT required — a float raises TypeError server-side
            guidance_scale=2.0,
            scheduler_type="euler",
            cfg_type="cfg",
            omega_scale=1.0,
            manual_seeds=str(model_seed),   # pinned -> reproducible song
            guidance_interval=0.05,
            guidance_interval_decay=0.99,
            min_guidance_scale=0.0,
            use_erg_tag=False,
            use_erg_lyric=False,
            use_erg_diffusion=False,
            oss_steps="",
            guidance_scale_text=1.5,
            guidance_scale_lyric=2.0,
            audio2audio_enable=False,
            ref_audio_strength=0.2,
            ref_audio_input=None,
            lora_name_or_path="none",
            api_name="/__call__",
        )

        audio = result[0] if isinstance(result, (list, tuple)) else result
        src = audio.get("path") if isinstance(audio, dict) else audio
        if not src or not os.path.exists(src):
            raise RuntimeError(f"ACE-Step returned unusable audio: {result!r}")

        dest = self._out_path(out_dir, f"song_{model_seed}", "wav")
        shutil.copyfile(src, dest)
        return GenerationResult(
            path=dest, mime="audio/wav",
            size_bytes=Path(dest).stat().st_size,
            license="Apache-2.0", model=SPACE,
            extra={"prompt": prompt, "seed": model_seed},
        )
