from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
GAME_DATA_ROOT = PACKAGE_ROOT / "game_versions"
VERIFIED_PROFILE_ROOT = PACKAGE_ROOT / "verified_profiles"


def load_game_data(game_version: str = "2.3") -> dict[str, Any]:
    normalized = game_version.replace(".", "_")
    path = GAME_DATA_ROOT / f"cp2077_{normalized}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No mapping data for game version {game_version}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def selector_range(data: dict[str, Any], key: str) -> tuple[int, int]:
    selector = data["selectors"][key]
    return int(selector["min"]), int(selector["max"])


def load_verified_profile(profile_id: str) -> dict[str, Any]:
    """Load an immutable, in-game-verified NPV regression profile."""
    if not profile_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for character in profile_id):
        raise ValueError(f"Invalid verified profile id: {profile_id!r}")
    path = VERIFIED_PROFILE_ROOT / f"{profile_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No verified NPV profile named {profile_id}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
