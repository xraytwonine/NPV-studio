from __future__ import annotations

import json
from pathlib import Path

from npv_studio.core.paths import PathGuard
from npv_studio.domain.models import CharacterConfig


def load_character(path: Path) -> CharacterConfig:
    return CharacterConfig.model_validate_json(path.read_text(encoding="utf-8"))


def save_character(path: Path, character: CharacterConfig, guard: PathGuard) -> Path:
    safe = guard.assert_write_path(path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(
        json.dumps(character.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return safe
