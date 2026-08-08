from __future__ import annotations

import json
import os
from pathlib import Path

from npv_studio.domain.models import AppSettings
from npv_studio.core.runtime import application_root


PROJECT_ROOT = application_root()
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "settings.json"


def _is_portable_release_root(path: Path) -> bool:
    name = path.name.casefold()
    return name.startswith("npv-studio-") and name.endswith("-win64")


def _relocate_stale_portable_paths(data: dict[str, object], settings_path: Path) -> bool:
    """Move bundled default paths from an older portable release to this one.

    Each portable ZIP is self-contained.  A settings file copied from a previous
    release may therefore contain absolute paths into that previous version's
    ``workspace`` directory.  Only those recognizable release-local defaults are
    migrated; user-selected paths elsewhere are deliberately preserved.
    """
    current_root = settings_path.resolve(strict=False).parent
    if not _is_portable_release_root(current_root):
        return False

    raw_workspace = data.get("workspace_root")
    if not isinstance(raw_workspace, str) or not raw_workspace.strip():
        return False

    old_workspace = Path(raw_workspace).resolve(strict=False)
    old_root = old_workspace.parent
    if (
        old_workspace.name.casefold() != "workspace"
        or not _is_portable_release_root(old_root)
        or old_root == current_root
    ):
        return False

    new_workspace = current_root / "workspace"
    data["workspace_root"] = str(new_workspace)
    for key, fallback_name in (
        ("preset_root", "presets"),
        ("package_output_root", "packages"),
    ):
        raw_path = data.get(key)
        if isinstance(raw_path, str) and raw_path.strip():
            configured = Path(raw_path).resolve(strict=False)
            try:
                relative = configured.relative_to(old_workspace)
            except ValueError:
                continue
            data[key] = str(new_workspace / relative)
        elif raw_path is None:
            data[key] = str(new_workspace / fallback_name)
    return True


def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> AppSettings:
    settings_path = Path(path)
    if not settings_path.is_file():
        save_settings(default_settings_for(settings_path.parent), settings_path)
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    migrated = _relocate_stale_portable_paths(data, settings_path)
    settings = AppSettings.model_validate(data)
    if migrated:
        save_settings(settings, settings_path)
    return settings


def default_settings() -> AppSettings:
    return default_settings_for(PROJECT_ROOT)


def default_settings_for(root: Path) -> AppSettings:
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    game_root = program_files_x86 / "Steam" / "steamapps" / "common" / "Cyberpunk 2077"
    workspace = Path(root).resolve(strict=False) / "workspace"
    return AppSettings(
        game_root=game_root,
        workspace_root=workspace,
        preset_root=workspace / "presets",
        package_output_root=workspace / "packages",
        install_enabled=False,
    )


def save_settings(settings: AppSettings, path: Path = DEFAULT_SETTINGS_PATH) -> Path:
    target = Path(path).resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(settings.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return target
