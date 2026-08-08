from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from npv_studio.core.paths import PathGuard
from npv_studio.domain.models import AppSettings, BodyFrame, BuildMode, CharacterConfig
from npv_studio.pipeline.appearance import (
    EYE_COLORS,
    EYE_MAKEUP_COLORS,
    FRECKLE_MAKEUP_COLORS,
    FEMALE_BIG_NIPPLES,
    FEMALE_BODY_TATTOOS,
    FEMALE_HAIR_STYLES,
    HAIR_COLORS,
    MALE_BLEMISH_COLORS,
    MALE_BODY_TATTOOS,
    MALE_HAIR_STYLES,
    NAIL_COLORS,
)
from npv_studio.pipeline.head import HeadTestBuilder, selected_head_components
from npv_studio.pipeline.creator_assets import BEARD_MESHES, BEARD_STYLE_CHUNK_MASKS
from npv_studio.pipeline.body_assets import (
    BODY_SCAR_CHUNK_MASKS,
    PUBIC_HAIR_COLORS,
    PUBIC_HAIR_STYLES,
)
from npv_studio.pipeline.npc_body_test import NpcBodyTestBuilder
from npv_studio.pipeline.package import PackageInspector, VortexPackageBuilder


class FinalBuildError(RuntimeError):
    """Raised before an incomplete or unverified package can be labelled final."""


ProgressCallback = Callable[[str], None]


class FinalBuildBuilder:
    """Generate a verified, spawnable, Vortex-importable NPV package.

    Every mutation is confined to ``workspace_root``. The game and reusable
    template roots are read-only inputs.
    """

    def __init__(
        self,
        settings: AppSettings,
        *,
        execute: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.settings = settings
        self.guard = PathGuard(settings.game_root, settings.workspace_root)
        self.execute = execute
        self.progress_callback = progress_callback or (lambda _message: None)

    def _progress(self, message: str) -> None:
        self.progress_callback(message)

    def _stage(self, number: int, message: str) -> None:
        self._progress(f"[{number}/9] {message}")

    def validate_character(self, character: CharacterConfig) -> None:
        selection = character.appearance
        errors: list[str] = []
        if selection.eye_color not in EYE_COLORS:
            errors.append(
                f"eye color {selection.eye_color} (available: {sorted(EYE_COLORS)})"
            )
        if selection.hair_color not in HAIR_COLORS:
            errors.append(
                f"hair color {selection.hair_color} (available: {sorted(HAIR_COLORS)})"
            )
        if selection.nail_color not in NAIL_COLORS:
            errors.append(
                f"nail color {selection.nail_color} (available: {sorted(NAIL_COLORS)})"
            )
        if selection.body_scars and selection.body_scars not in BODY_SCAR_CHUNK_MASKS:
            errors.append(
                f"body scars {selection.body_scars} (available: {sorted(BODY_SCAR_CHUNK_MASKS)})"
            )
        penis_selected = selection.genitals.startswith("penis")
        if penis_selected and selection.penis_size == "unavailable":
            errors.append("penis size must be Small, Default, or Big when a penis is selected")
        if not penis_selected and selection.penis_size != "unavailable":
            errors.append("penis size must be Unavailable unless Penis 1 or Penis 2 is selected")
        if selection.pubic_hair_style:
            if selection.genitals == "none":
                errors.append("pubic hair requires a selected genital geometry")
            if selection.pubic_hair_style not in PUBIC_HAIR_STYLES:
                errors.append(
                    f"pubic hair style {selection.pubic_hair_style} "
                    f"(available: {sorted(PUBIC_HAIR_STYLES)})"
                )
            if selection.pubic_hair_color not in PUBIC_HAIR_COLORS:
                errors.append(
                    f"pubic hair color {selection.pubic_hair_color} "
                    f"(available: {sorted(PUBIC_HAIR_COLORS)})"
                )
        if (
            1 <= selection.cheek_makeup <= 4
            and selection.cheek_makeup_color not in FRECKLE_MAKEUP_COLORS
        ):
            errors.append(
                "cheek/freckle color "
                f"{selection.cheek_makeup_color} (styles 1-4 support: "
                f"{sorted(FRECKLE_MAKEUP_COLORS)})"
            )
        if character.body_frame is BodyFrame.FEMALE:
            supported = sorted(FEMALE_HAIR_STYLES)
            if selection.hairstyle not in FEMALE_HAIR_STYLES:
                errors.append(f"hairstyle {selection.hairstyle} (available: {supported})")
            if selection.eyebrow_color not in HAIR_COLORS:
                errors.append(
                    f"eyebrow color {selection.eyebrow_color} (available: {sorted(HAIR_COLORS)})"
                )
            if selection.eye_makeup and selection.eye_makeup_color not in EYE_MAKEUP_COLORS:
                errors.append(
                    "eye-makeup color "
                    f"{selection.eye_makeup_color} (available: {sorted(EYE_MAKEUP_COLORS)})"
                )
            if selection.body_tattoos and (
                selection.body_tattoos not in FEMALE_BODY_TATTOOS["default"]
                or selection.body_tattoos not in FEMALE_BODY_TATTOOS["big"]
            ):
                errors.append(
                    "body tattoo "
                    f"{selection.body_tattoos} (available dual-body pair: "
                    f"{sorted(FEMALE_BODY_TATTOOS['default'])})"
                )
            if selection.nipples and selection.nipples not in FEMALE_BIG_NIPPLES:
                errors.append(
                    f"nipple selection {selection.nipples} "
                    f"(available: {sorted(FEMALE_BIG_NIPPLES)})"
                )
            if selection.beard:
                errors.append("beards are unavailable for the feminine body frame")
        else:
            if selection.hairstyle not in MALE_HAIR_STYLES:
                errors.append(
                    f"hairstyle {selection.hairstyle} (available: {sorted(MALE_HAIR_STYLES)})"
                )
            if selection.blemishes and selection.blemish_color not in MALE_BLEMISH_COLORS:
                errors.append(
                    f"blemish color {selection.blemish_color} "
                    f"(available: {sorted(MALE_BLEMISH_COLORS)})"
                )
            if selection.body_tattoos and selection.body_tattoos not in MALE_BODY_TATTOOS:
                errors.append(
                    f"body tattoo {selection.body_tattoos} "
                    f"(available: {sorted(MALE_BODY_TATTOOS)})"
                )
            if selection.nipples:
                errors.append("nipples are unavailable for the masculine body frame")
            if selection.beard:
                if selection.beard not in BEARD_MESHES:
                    errors.append(
                        f"beard {selection.beard} (available: {sorted(BEARD_MESHES)})"
                    )
                elif selection.beard_style not in BEARD_STYLE_CHUNK_MASKS[selection.beard]:
                    errors.append(
                        f"beard style {selection.beard_style} for beard {selection.beard} "
                        f"(available: {sorted(BEARD_STYLE_CHUNK_MASKS[selection.beard])})"
                    )
                if selection.beard > 1 and selection.beard_color not in HAIR_COLORS:
                    errors.append(
                        f"beard color {selection.beard_color} (available: {sorted(HAIR_COLORS)})"
                    )
        if errors:
            raise FinalBuildError(
                "Selections without an available asset mapping:\n- " + "\n- ".join(errors)
            )
        selected_head_components(character)

    def _require_dependencies(self) -> None:
        missing: list[str] = []
        for label, path in (
            ("Cyberpunk 2077", self.settings.game_root / "bin" / "x64" / "Cyberpunk2077.exe"),
            ("WolvenKit CLI", self.settings.wolvenkit_executable),
            ("Blender", self.settings.blender_executable),
            ("WolvenKit Blender IO Suite", self.settings.blender_addon_root),
            ("NPV template", self.settings.npv_template_root),
        ):
            if path is None or not Path(path).exists():
                missing.append(label)
        if missing:
            raise FinalBuildError("Missing final-build dependencies: " + ", ".join(missing))

    def ensure_isolated_template(self, frame: BodyFrame) -> Path:
        source_template = self.settings.npv_template_root
        if source_template is None:
            raise FinalBuildError("No reusable NPV template root is configured")
        source_root = Path(source_template).resolve(strict=True) / "source"
        character_directory = (
            "your_male_character" if frame is BodyFrame.MALE else "your_female_character"
        )
        lua_name = (
            "tutorial_custom_male_character.lua"
            if frame is BodyFrame.MALE
            else "tutorial_custom_female_character.lua"
        )
        cache = self.guard.assert_write_path(
            self.settings.workspace_root / "integration" / "templates" / "v1" / frame.value
        )
        required = (
            cache / "source" / "archive" / "tutorial" / "npv" / character_directory,
            cache / "source" / "raw" / "tutorial" / "npv" / character_directory,
            cache
            / "source"
            / "resources"
            / "bin"
            / "x64"
            / "plugins"
            / "cyber_engine_tweaks"
            / "mods"
            / "AppearanceMenuMod"
            / "Collabs"
            / "Custom Entities"
            / "tutorial"
            / lua_name,
        )
        if all(path.exists() for path in required):
            return cache
        if cache.exists():
            raise FinalBuildError(
                f"The isolated {frame.value} template cache is incomplete: {cache}. "
                "Remove or rename that workspace cache before rebuilding it."
            )

        archive_source = source_root / "archive" / "tutorial" / "npv" / character_directory
        raw_source = source_root / "raw" / "tutorial" / "npv" / character_directory
        lua_source = (
            source_root
            / "resources"
            / "bin"
            / "x64"
            / "plugins"
            / "cyber_engine_tweaks"
            / "mods"
            / "AppearanceMenuMod"
            / "Collabs"
            / "Custom Entities"
            / "tutorial"
            / lua_name
        )
        for path in (archive_source, raw_source, lua_source):
            if not path.exists():
                raise FinalBuildError(f"Required reusable template resource is missing: {path}")

        shutil.copytree(archive_source, required[0])
        shutil.copytree(raw_source, required[1])
        required[2].parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lua_source, required[2])
        return cache

    def build(self, character: CharacterConfig) -> dict[str, Any]:
        if not self.execute:
            raise FinalBuildError("Final generation requires explicit execution")
        self._stage(1, "Validating creator selections and required tools")
        self._require_dependencies()
        self.validate_character(character)
        character = character.model_copy(
            update={
                "output": character.output.model_copy(update={"mode": BuildMode.FINAL})
            }
        )
        self._stage(2, f"Preparing the isolated {character.body_frame.value} NPV template")
        template = self.ensure_isolated_template(character.body_frame)

        self._stage(3, "Baking head and selected body assets with Blender and WolvenKit")
        head = HeadTestBuilder(self.settings, execute=True).build(
            character, template, package_output=False, final=True
        )
        if character.body_frame is BodyFrame.FEMALE:
            self._stage(4, "Compiling persistent normal/big body toggles and seam fix")
            completed = NpcBodyTestBuilder(
                self.settings, execute=True, profile="dual_body"
            ).build(
                Path(head["build_root"]),
                character=character,
                final=True,
                package_output=False,
            )
        else:
            self._stage(4, "Finalizing masculine body and disabled penis toggles")
            completed = head

        self._stage(5, "Verifying the compiled runtime staging tree")
        staging = Path(completed["build_root"]) / "staging"
        if not staging.is_dir():
            raise FinalBuildError(f"Final staging directory is missing: {staging}")
        archives = list((staging / "archive" / "pc" / "mod").glob("*.archive"))
        if len(archives) != 1:
            raise FinalBuildError(f"Expected one runtime archive in staging, found {len(archives)}")
        self._stage(6, "Normalizing the archive and AMM registration")
        final_archive = archives[0].with_name(f"npv_studio_{character.namespace}.archive")
        if archives[0] != final_archive:
            archives[0].rename(final_archive)

        self._stage(7, "Creating the minimized Vortex ZIP")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        package_output_root = self.settings.package_output_root or (
            self.settings.workspace_root / "packages"
        )
        self.guard.ensure_export_directory(package_output_root)
        package_path = package_output_root / (
            f"{character.namespace}_npv_{stamp}.zip"
        )
        package = VortexPackageBuilder(self.guard).build(
            staging,
            package_path,
            mod_name=f"{character.name} NPV",
            version="1.0.0",
            export_root=package_output_root,
        )
        self._stage(8, "Inspecting package structure and deployment safety")
        inspection = PackageInspector().inspect_zip(package_path)
        if not inspection["valid"]:
            raise FinalBuildError("Final package inspection failed: " + "; ".join(inspection["errors"]))

        report = {
            "schema_version": 1,
            "status": "spawnable_vortex_package_ready",
            "character": character.model_dump(mode="json"),
            "template_cache": str(template),
            "pipeline_build_root": completed["build_root"],
            "package": package,
            "inspection": inspection,
            "unsupported_preserved_fields": [],
            "safety": {
                "game_root": str(self.settings.game_root),
                "game_root_access": "read_only",
                "direct_game_writes": False,
                "vortex_writes": False,
                "installation_owner": "Vortex",
            },
        }
        report_path = self.guard.write_text(
            Path(completed["build_root"]) / "reports" / "final-build-report.json",
            json.dumps(report, indent=2) + "\n",
        )
        report["report_path"] = str(report_path)
        self._stage(9, f"Ready: {package_path}")
        return report
