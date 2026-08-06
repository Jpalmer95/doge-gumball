"""3D asset generation: concept image (FLUX) -> alpha mask -> TRELLIS.2 -> GLB.

Chain (endpoints verified against the live Space with gradio_client 2.5.0):
    /start_session
    /preprocess_image(image)                  -> alpha-masked RGBA
    /get_seed(randomize_seed, seed)           -> seed
    /image_to_3d(image, seed, resolution,
                 s1g, s1r, s1steps, s1rescale,
                 s2g, s2r, s2steps, s2rescale,
                 s3g, s3r, s3steps, s3rescale) -> 3D preview
    /extract_glb(decimation_target, texture_size) -> (glb_path, download)

Output license: MIT (Microsoft TRELLIS/TRELLIS.2). Cost: 0 USD — machine's
ZeroGPU quota. Slow: expect 1-4 minutes; retry with the same model_seed to
reuse the server-side cache when extraction times out.
"""
import os
import shutil
from pathlib import Path

from .base import Generator, GenerationResult, resolve_token
from .image_flux import FluxImageGenerator

SPACE = "microsoft/TRELLIS.2"
STAGE_PARAMS = (7.5, 0.7, 12, 5, 7.5, 0.7, 12, 5, 1.0, 0.0, 12, 3)


class Trellis3DGenerator(Generator):
    name = "asset_3d_trellis"
    requires_network = True
    live = True

    def generate(self, prompt: str, model_seed: int, out_dir: str) -> GenerationResult:
        token = resolve_token()
        if not token:
            raise RuntimeError("HF_TOKEN not set — required for ZeroGPU Space quota")

        from gradio_client import Client

        client = Client(SPACE, token=token, verbose=False)

        # 1) concept image via FLUX (same model seed -> reproducible concept)
        concept = FluxImageGenerator().generate(prompt, model_seed, out_dir)
        concept_path = concept.path

        # 2) session + preprocessing
        client.predict(api_name="/start_session")
        masked = client.predict(concept_path, api_name="/preprocess_image")
        masked_path = masked.get("path") if isinstance(masked, dict) else masked

        # 3) deterministic seed (do NOT randomize — fairness requires it)
        seed_out = client.predict(False, model_seed, api_name="/get_seed")
        seed = seed_out if isinstance(seed_out, int) else seed_out[0]

        # 4) generate mesh
        client.predict(
            masked_path, seed, 512, *STAGE_PARAMS, api_name="/image_to_3d"
        )

        # 5) extract GLB (retries reuse the cached generation)
        glb = None
        for attempt in range(3):
            try:
                glb = client.predict(300000, 2048, api_name="/extract_glb")
                break
            except Exception:
                if attempt == 2:
                    raise
        if isinstance(glb, (list, tuple)):
            glb = glb[0]
        glb_path = glb.get("path") if isinstance(glb, dict) else glb
        if not glb_path or not os.path.exists(glb_path):
            raise RuntimeError(f"TRELLIS returned unusable GLB: {glb!r}")

        dest = self._out_path(out_dir, f"3d_{model_seed}", "glb")
        shutil.copyfile(glb_path, dest)
        return GenerationResult(
            path=dest, mime="model/gltf-binary",
            size_bytes=Path(dest).stat().st_size,
            license="MIT", model=SPACE,
            extra={"prompt": prompt, "concept_image": concept_path, "seed": seed},
        )
