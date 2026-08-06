"""FLUX.1-schnell image generation via the official HF Space.

Output license: Apache-2.0 (Black Forest Labs). Cost: 0 USD — runs on the
machine's own HF ZeroGPU quota (HF_TOKEN Space secret). See
docs/license-audit.md and docs/cost-ledger.md.
"""
import os
import shutil
from pathlib import Path

from .base import Generator, GenerationResult, resolve_token

SPACE = "black-forest-labs/FLUX.1-schnell"
ENDPOINT = "/infer"


class FluxImageGenerator(Generator):
    name = "image_flux"
    requires_network = True
    live = True

    def generate(self, prompt: str, model_seed: int, out_dir: str) -> GenerationResult:
        token = resolve_token()
        if not token:
            raise RuntimeError("HF_TOKEN not set — required for ZeroGPU Space quota")

        from gradio_client import Client

        client = Client(SPACE, token=token, verbose=False)
        # Official space /infer signature: (prompt, seed, randomize_seed)
        result = client.predict(
            prompt,
            model_seed,
            False,
            api_name=ENDPOINT,
        )
        src = result
        if isinstance(result, (list, tuple)):
            src = result[0]
        if isinstance(src, dict):
            src = src.get("path") or src.get("url")
        if not src or not os.path.exists(src):
            raise RuntimeError(f"FLUX returned unusable result: {result!r}")

        dest = self._out_path(out_dir, f"img_{model_seed}", "png")
        shutil.copyfile(src, dest)
        return GenerationResult(
            path=dest, mime="image/png",
            size_bytes=Path(dest).stat().st_size,
            license="Apache-2.0", model=SPACE,
            extra={"prompt": prompt},
        )
