"""Generator interface. Every generator must be deterministic in *what* it
produces (given the spec's model_seed + prompt) and must declare its output
license so the machine can stamp CC0 dedication on the receipt.
"""
from dataclasses import dataclass, field
import os
from pathlib import Path

from .. import config


def resolve_token() -> str | None:
    """HF token lookup order: env vars, then the hf CLI cache (~/.cache/hf)."""
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        if os.environ.get(key):
            return os.environ[key].strip()
    cache = Path.home() / ".cache" / "huggingface" / "token"
    if cache.exists():
        tok = cache.read_text().strip()
        if tok:
            return tok
    return None


@dataclass
class GenerationResult:
    path: str                 # absolute or cwd-relative path to the asset
    mime: str
    size_bytes: int
    license: str              # e.g. "CC0-1.0", "Apache-2.0"
    model: str                # model / space used
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "mime": self.mime,
            "size_bytes": self.size_bytes,
            "license": self.license,
            "model": self.model,
            **self.extra,
        }


class Generator:
    name: str = "base"
    requires_network: bool = False
    live: bool = True         # False = offline/procedural, always available

    def generate(self, prompt: str, model_seed: int, out_dir: str) -> GenerationResult:
        raise NotImplementedError

    # -- helpers -----------------------------------------------------------
    def _out_path(self, out_dir: str, tx_tag: str, ext: str) -> str:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        return str(Path(out_dir) / f"{tx_tag}.{ext}")
