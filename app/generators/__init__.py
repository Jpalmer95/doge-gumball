"""Generator registry — the machine dispatches to these by category.

Ordering rule for the machine: retry the SAME category on failure (fairness
demands the drawn prize never silently changes). Availability flags let the
operator disable a category that is temporarily broken; the machine then
re-draws from the remaining categories for blind gumballs only.
"""
from .asset_3d_trellis import Trellis3DGenerator
from .base import Generator
from .game_sfx import SfxGenerator
from .image_flux import FluxImageGenerator
from .song_acestep import AceStepSongGenerator

REGISTRY: dict[str, Generator] = {
    "image": FluxImageGenerator(),
    "asset_3d": Trellis3DGenerator(),
    "song": AceStepSongGenerator(),
    "game_sfx": SfxGenerator(),
}

# Categories the operator has verified end-to-end in the live machine.
# All four were dispensed through machine.dispense with real draws on
# 2026-08-06 (image/3d/song via ZeroGPU Spaces, sfx procedural).
LIVE_CATEGORIES = ["image", "asset_3d", "song", "game_sfx"]
PENDING_LIVE_CATEGORIES: list[str] = []


def get(category: str) -> Generator:
    return REGISTRY[category]
