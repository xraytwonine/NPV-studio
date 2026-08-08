from __future__ import annotations

import shutil
from pathlib import Path

from npv_studio.core.paths import PathGuard
from npv_studio.domain.models import AppSettings, DependencyKind, DependencyStatus


def _configured_or_path(configured: Path | None, *command_names: str) -> Path | None:
    if configured is not None and configured.is_file():
        return configured.resolve(strict=False)
    for name in command_names:
        discovered = shutil.which(name)
        if discovered:
            return Path(discovered).resolve(strict=False)
    return None


def _template_inventory(root: Path | None) -> dict[str, int]:
    extensions = {".app", ".ent", ".mesh", ".morphtarget", ".blend", ".lua"}
    inventory = {extension: 0 for extension in extensions}
    if root is None or not root.is_dir():
        return inventory
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in inventory:
            inventory[path.suffix.lower()] += 1
    return inventory


class DependencyInspector:
    def __init__(self, settings: AppSettings, guard: PathGuard) -> None:
        self.settings = settings
        self.guard = guard

    def inspect(self) -> list[DependencyStatus]:
        game_root = self.guard.assert_game_read_path(self.settings.game_root)
        game_exe = game_root / "bin" / "x64" / "Cyberpunk2077.exe"
        amm_path = (
            game_root
            / "bin"
            / "x64"
            / "plugins"
            / "cyber_engine_tweaks"
            / "mods"
            / "AppearanceMenuMod"
        )
        codeware_path = game_root / "red4ext" / "plugins" / "Codeware"
        blender = _configured_or_path(self.settings.blender_executable, "blender", "blender.exe")
        blender_addon = self.settings.blender_addon_root
        wolvenkit_gui = _configured_or_path(self.settings.wolvenkit_gui_executable)
        wolvenkit = _configured_or_path(
            self.settings.wolvenkit_executable,
            "wolvenkit.cli",
            "wolvenkit.cli.exe",
            "cp77tools",
            "cp77tools.exe",
        )
        template = self.settings.npv_template_root
        inventory = _template_inventory(template)
        template_has_core = all(inventory[extension] > 0 for extension in (".app", ".ent", ".mesh", ".morphtarget"))

        return [
            DependencyStatus(
                name="Cyberpunk 2077",
                available=game_exe.is_file(),
                path=game_root,
                required_for_dry_run=True,
                details="Read-only source. NPV Studio never writes here.",
            ),
            DependencyStatus(
                name="Appearance Menu Mod",
                available=amm_path.is_dir(),
                path=amm_path if amm_path.is_dir() else None,
                kind=DependencyKind.RUNTIME_MOD,
                details="Required in-game for spawning the generated entity.",
            ),
            DependencyStatus(
                name="Codeware",
                available=codeware_path.is_dir(),
                path=codeware_path if codeware_path.is_dir() else None,
                kind=DependencyKind.RUNTIME_MOD,
                details="Required in-game by Appearance Creator Mod; it is not used to build the ZIP.",
            ),
            DependencyStatus(
                name="Blender",
                available=blender is not None,
                path=blender,
                details=(
                    "Validated for unattended head morph baking in the final workspace-only pipeline."
                    if blender
                    else "Required for head morph baking in a spawnable build."
                ),
            ),
            DependencyStatus(
                name="WolvenKit Blender IO Suite",
                available=bool(blender_addon and (blender_addon / "__init__.py").is_file()),
                path=(
                    blender_addon.resolve(strict=False)
                    if blender_addon and (blender_addon / "__init__.py").is_file()
                    else None
                ),
                details="Required Blender add-on for Cyberpunk resource import and export.",
            ),
            DependencyStatus(
                name="WolvenKit desktop",
                available=wolvenkit_gui is not None,
                path=wolvenkit_gui,
                kind=DependencyKind.OPTIONAL,
                details=(
                    "Desktop GUI detected for manual inspection; it is not used as the automation CLI."
                    if wolvenkit_gui
                    else "Optional desktop GUI for manual resource inspection."
                ),
            ),
            DependencyStatus(
                name="WolvenKit CLI",
                available=wolvenkit is not None,
                path=wolvenkit,
                details="Required for REDengine import, conversion, validation, and packing.",
            ),
            DependencyStatus(
                name="NPV template resources",
                available=template_has_core,
                path=template.resolve(strict=False) if template_has_core and template else None,
                details=(
                    "Template candidate inventoried: "
                    + ", ".join(f"{key}={value}" for key, value in sorted(inventory.items()))
                    + ". Feminine and masculine branches are copied into isolated workspace caches."
                    if template_has_core
                    else "Requires prepared .app, .ent, .mesh, and .morphtarget resources."
                ),
            ),
        ]
