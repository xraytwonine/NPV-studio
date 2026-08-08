from __future__ import annotations

import sys
from pathlib import Path


def application_root() -> Path:
    """Writable portable root beside the executable (or project root in development)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def bundled_resource_root() -> Path:
    """Read-only root containing packaged Blender workers and templates."""
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle).resolve() if bundle else application_root()
