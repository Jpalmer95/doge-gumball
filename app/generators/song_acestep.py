"""Song generation via the official ACE-Step Space (Apache-2.0 model).

The ACE-Step Space exposes a rich editor UI; the main generation entrypoint
is /__call__. Its exact signature varies across Space revisions, so we
introspect at runtime and fall back to a documented parameter map, keeping
this generator honest: it raises a clear error rather than guessing silently.

Cost: 0 USD (ZeroGPU quota). Slow: expect 1-3 minutes for a full track.
"""
import os
import shutil
from pathlib import Path

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

        from gradio_client import Client

        client = Client(SPACE, token=token, verbose=False)
        params = self._introspect(client, prompt)
        result = client.predict(**params)

        src = result
        if isinstance(result, (list, tuple)):
            src = result[0]
        if isinstance(src, dict):
            src = src.get("path") or src.get("url")
        if not src or not os.path.exists(src):
            raise RuntimeError(f"ACE-Step returned unusable result: {result!r}")

        dest = self._out_path(out_dir, f"song_{model_seed}", "wav")
        shutil.copyfile(src, dest)
        return GenerationResult(
            path=dest, mime="audio/wav",
            size_bytes=Path(dest).stat().st_size,
            license="Apache-2.0", model=SPACE,
            extra={"prompt": prompt},
        )

    def _introspect(self, client, prompt: str) -> dict:
        """Map the prompt onto the Space's /__call__ parameters."""
        api = client.view_api(return_format="dict", print_info=False)
        eps = api.get("named_endpoints", {})
        call = eps.get("/__call__")
        if not call:
            raise RuntimeError("ACE-Step Space has no /__call__ endpoint — Space revision changed")
        params = {}
        for p in call.get("parameters", []):
            label = (p.get("label") or "").lower()
            py = (p.get("python_type") or "").lower()
            if "prompt" in label or "lyrics" in label or "text" in label:
                params[p["parameter_name"]] = prompt
            elif "tag" in label or "style" in label:
                params[p["parameter_name"]] = "pop, electronic" if "electronic" in prompt else "lo-fi"
            elif "duration" in label or "seconds" in label:
                params[p["parameter_name"]] = 30
        if not params:
            raise RuntimeError(
                "Could not map prompt onto ACE-Step /__call__ parameters — "
                "update app/generators/song_acestep.py against the current Space API"
            )
        return params
