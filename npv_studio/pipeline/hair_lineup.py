from __future__ import annotations

import hashlib
import json
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from npv_studio.adapters.process import ExternalToolRunner, ProcessResult
from npv_studio.core.paths import PathGuard, is_within
from npv_studio.domain.models import AppSettings, CharacterConfig
from npv_studio.pipeline.appearance import (
    compile_female_appearance_document,
    female_hair_resource_paths,
)
from npv_studio.pipeline.package import VortexPackageBuilder
from npv_studio.pipeline.head import selected_female_head_components
from npv_studio.pipeline.runtime_resources import prune_female_runtime_resources


HAIR_LINEUP = (8, 11, 42, 33, 24)
SOURCE_APP_PATH = "tutorial\\npv\\your_female_character\\_your_female_character.app"
APPEARANCE_NAMES = ("tutorial_woman_casual", "tutorial_woman_business")


class HairLineupBuildError(RuntimeError):
    """Raised when the independently spawnable hairstyle lineup cannot be built."""


def _require_success(stage: str, result: ProcessResult) -> None:
    if result.returncode != 0:
        raise HairLineupBuildError(
            f"{stage} failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _process_data(result: ProcessResult) -> dict[str, Any]:
    return {
        "command": list(result.command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _replace_resource_path(node: Any, old: str, new: str) -> int:
    replacements = 0
    if isinstance(node, dict):
        if node.get("$value") == old:
            node["$value"] = new
            replacements += 1
        for value in node.values():
            replacements += _replace_resource_path(value, old, new)
    elif isinstance(node, list):
        for value in node:
            replacements += _replace_resource_path(value, old, new)
    return replacements


def _amm_lua(hair: int, entity_path: str) -> str:
    lua_path = entity_path.replace("\\", "\\\\")
    appearances = ",\n".join(f'    "{name}"' for name in APPEARANCE_NAMES)
    return f'''return {{
  modder = "NPV Studio",
  unique_identifier = "npv_studio_tutorial_woman_hair_{hair:02d}",
  entity_info = {{
    name = "Tutorial Woman {hair}",
    path = "{lua_path}",
    record = "Character.afterlife_merc_fast_melee_w_hard",
    type = "Character",
    customName = true
  }},
  appearances = {{
{appearances}
  }},
  attributes = {{}},
}}
'''


class HairLineupBuilder:
    """Clone a verified template-backed NPV into five independent hair tests."""

    def __init__(self, settings: AppSettings, *, execute: bool = False) -> None:
        self.settings = settings
        self.guard = PathGuard(settings.game_root, settings.workspace_root)
        self.runner = ExternalToolRunner(self.guard, enabled=execute)

    def build(self, base_build: Path) -> dict[str, Any]:
        if not self.runner.enabled:
            raise HairLineupBuildError("Hair lineup generation requires the explicit --execute flag")
        wolvenkit = self.settings.wolvenkit_executable
        if wolvenkit is None or not wolvenkit.is_file():
            raise HairLineupBuildError("A valid WolvenKit CLI executable is required")

        base = Path(base_build).resolve(strict=True)
        if not is_within(base, self.settings.workspace_root):
            raise HairLineupBuildError("The verified base build must be inside the configured workspace")
        base_source = base / "source" if (base / "source").is_dir() else base
        if not (base_source / "archive").is_dir():
            raise HairLineupBuildError(f"Base build has no source/archive directory: {base_source}")

        original_resource_root = (
            base_source / "archive" / "tutorial" / "npv" / "your_female_character"
        )
        original_app = original_resource_root / "_your_female_character.app"
        original_ent = original_resource_root / "_your_female_character.ent"
        if not original_app.is_file() or not original_ent.is_file():
            raise HairLineupBuildError(
                "The verified base build is missing the tutorial woman's .app or .ent resource"
            )

        report_root = base if (base / "reports").is_dir() else base.parent
        head_report_path = report_root / "reports" / "head-build-report.json"
        if not head_report_path.is_file():
            raise HairLineupBuildError(
                f"The verified base build has no head-build report: {head_report_path}"
            )
        head_report = json.loads(head_report_path.read_text(encoding="utf-8"))
        character = CharacterConfig.model_validate(head_report["character"])
        template_project = Path(head_report["template_project"]).resolve(strict=True)
        clean_template_app = (
            template_project
            / "source"
            / "archive"
            / "tutorial"
            / "npv"
            / "your_female_character"
            / "_your_female_character.app"
        )
        if not clean_template_app.is_file():
            raise HairLineupBuildError(
                f"The clean template app referenced by the head report is missing: {clean_template_app}"
            )

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        build_id = f"tutorial_women_hair_lineup_{stamp}"
        build_root = self.guard.assert_write_path(
            self.settings.workspace_root / "integration" / "hair_lineups" / build_id
        )
        if build_root.exists():
            raise HairLineupBuildError(f"Refusing to overwrite an existing build: {build_root}")
        source_root = build_root / "source"
        shutil.copytree(base_source, source_root)

        resource_root = source_root / "archive" / "tutorial" / "npv" / "your_female_character"
        source_app = resource_root / "_your_female_character.app"
        source_ent = resource_root / "_your_female_character.ent"
        json_root = self.guard.ensure_directory(build_root / "resource_json")
        processes: dict[str, Any] = {}

        required_hair_resources = sorted(
            {
                resource
                for hairstyle in HAIR_LINEUP
                for resource in female_hair_resource_paths(hairstyle)
            }
        )
        appearance_archive = self.guard.assert_game_read_path(
            self.settings.game_root
            / "archive"
            / "pc"
            / "content"
            / "basegame_4_appearance.archive"
        )
        if not appearance_archive.is_file():
            raise HairLineupBuildError(f"Base-game appearance archive is missing: {appearance_archive}")
        resource_regex = "^(?:" + "|".join(re.escape(path) for path in required_hair_resources) + ")$"
        archive_result = self.runner.run(
            wolvenkit,
            ["archiveinfo", str(appearance_archive), "--list", "--regex", resource_regex],
            build_root,
        )
        processes["validate_hair_resources"] = _process_data(archive_result)
        _require_success("Native hairstyle resource validation", archive_result)
        found_hair_resources = {
            line.strip()
            for line in archive_result.stdout.splitlines()
            if line.strip().casefold().startswith("base\\")
        }
        missing_hair_resources = [
            path
            for path in required_hair_resources
            if path.casefold() not in {found.casefold() for found in found_hair_resources}
        ]
        if missing_hair_resources:
            raise HairLineupBuildError(
                "Native hairstyle definitions reference missing resources: "
                + ", ".join(missing_hair_resources)
            )

        app_json_root = self.guard.ensure_directory(json_root / "source_app")
        app_serialize = self.runner.run(
            wolvenkit,
            ["convert", "serialize", str(clean_template_app), "--outpath", str(app_json_root)],
            build_root,
        )
        processes["serialize_clean_template_app"] = _process_data(app_serialize)
        _require_success("Clean template app serialization", app_serialize)
        app_json = app_json_root / "_your_female_character.app.json"
        if not app_json.is_file():
            raise HairLineupBuildError(f"WolvenKit did not create {app_json}")
        app_document = json.loads(app_json.read_text(encoding="utf-8"))

        ent_json_root = self.guard.ensure_directory(json_root / "source_ent")
        ent_serialize = self.runner.run(
            wolvenkit,
            ["convert", "serialize", str(source_ent), "--outpath", str(ent_json_root)],
            build_root,
        )
        processes["serialize_source_ent"] = _process_data(ent_serialize)
        _require_success("Source entity serialization", ent_serialize)
        ent_json = ent_json_root / "_your_female_character.ent.json"
        if not ent_json.is_file():
            raise HairLineupBuildError(f"WolvenKit did not create {ent_json}")
        ent_document = json.loads(ent_json.read_text(encoding="utf-8"))

        clones: list[dict[str, Any]] = []
        generated_lua: list[Path] = []
        for hair in HAIR_LINEUP:
            slug = f"tutorial_woman_{hair:02d}"
            depot_directory = f"tutorial\\npv\\hair_tests\\{slug}"
            app_depot_path = f"{depot_directory}\\{slug}.app"
            ent_depot_path = f"{depot_directory}\\{slug}.ent"
            clone_root = source_root / "archive" / Path(*depot_directory.split("\\"))
            clone_root.mkdir(parents=True, exist_ok=True)

            clone_json_root = self.guard.ensure_directory(json_root / f"hair_{hair:02d}")
            clone_app_document = deepcopy(app_document)
            clone_character_data = character.model_dump(mode="python")
            clone_character_data["appearance"]["hairstyle"] = hair
            clone_character = CharacterConfig.model_validate(clone_character_data)
            appearance_report = compile_female_appearance_document(
                clone_app_document, clone_character
            )
            clone_app_json = self.guard.write_text(
                clone_json_root / f"{slug}.app.json",
                json.dumps(clone_app_document, indent=2) + "\n",
            )
            app_deserialize = self.runner.run(
                wolvenkit,
                ["convert", "deserialize", str(clone_app_json), "--outpath", str(clone_root)],
                build_root,
            )
            processes[f"deserialize_app_{hair:02d}"] = _process_data(app_deserialize)
            _require_success(f"Hair {hair} app deserialization", app_deserialize)
            clone_app = clone_root / f"{slug}.app"
            if not clone_app.is_file():
                raise HairLineupBuildError(f"WolvenKit did not create {clone_app}")

            clone_ent_document = deepcopy(ent_document)
            replacement_count = _replace_resource_path(
                clone_ent_document, SOURCE_APP_PATH, app_depot_path
            )
            if replacement_count != len(APPEARANCE_NAMES):
                raise HairLineupBuildError(
                    f"Hair {hair} entity expected {len(APPEARANCE_NAMES)} app references; "
                    f"replaced {replacement_count}"
                )
            clone_ent_json = self.guard.write_text(
                clone_json_root / f"{slug}.ent.json",
                json.dumps(clone_ent_document, indent=2) + "\n",
            )
            ent_deserialize = self.runner.run(
                wolvenkit,
                ["convert", "deserialize", str(clone_ent_json), "--outpath", str(clone_root)],
                build_root,
            )
            processes[f"deserialize_ent_{hair:02d}"] = _process_data(ent_deserialize)
            _require_success(f"Hair {hair} entity deserialization", ent_deserialize)
            clone_ent = clone_root / f"{slug}.ent"
            if not clone_ent.is_file():
                raise HairLineupBuildError(f"WolvenKit did not create {clone_ent}")

            lua_path = self.guard.write_text(
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
                / "npv_studio_hair_tests"
                / f"{slug}.lua",
                _amm_lua(hair, ent_depot_path),
            )
            generated_lua.append(lua_path)
            clones.append(
                {
                    "display_name": f"Tutorial Woman {hair}",
                    "hairstyle": hair,
                    "entity_depot_path": ent_depot_path,
                    "app_depot_path": app_depot_path,
                    "unique_identifier": f"npv_studio_tutorial_woman_hair_{hair:02d}",
                    "app_sha256": _sha256(clone_app),
                    "ent_sha256": _sha256(clone_ent),
                    "appearance_names": list(APPEARANCE_NAMES),
                    "appearance": appearance_report,
                }
            )

        # These two records would reintroduce the single original Tutorial Woman
        # and can conflict with earlier test packages. The shared meshes remain.
        source_app.unlink()
        source_ent.unlink()
        original_lua = (
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
            / "tutorial_custom_female_character.lua"
        )
        if original_lua.is_file():
            original_lua.unlink()

        runtime_pruning = prune_female_runtime_resources(
            self.guard,
            source_root / "archive",
            (mesh_stem for mesh_stem, _ in selected_female_head_components(character)),
        )

        compiled_root = self.guard.ensure_directory(build_root / "compiled")
        pack_result = self.runner.run(
            wolvenkit,
            ["pack", str(source_root / "archive"), "--outpath", str(compiled_root)],
            build_root,
        )
        processes["pack"] = _process_data(pack_result)
        _require_success("Hair lineup archive pack", pack_result)
        archives = sorted(compiled_root.glob("*.archive"))
        if len(archives) != 1:
            raise HairLineupBuildError(f"Expected one packed archive, found {len(archives)}")

        staging = self.guard.ensure_directory(build_root / "staging")
        archive_target = (
            staging / "archive" / "pc" / "mod" / "npv_studio_tutorial_women_hair_lineup.archive"
        )
        archive_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archives[0], archive_target)
        lua_stage_root = (
            staging
            / "bin"
            / "x64"
            / "plugins"
            / "cyber_engine_tweaks"
            / "mods"
            / "AppearanceMenuMod"
            / "Collabs"
            / "Custom Entities"
            / "npv_studio_hair_tests"
        )
        lua_stage_root.mkdir(parents=True, exist_ok=True)
        for lua_path in generated_lua:
            shutil.copy2(lua_path, lua_stage_root / lua_path.name)

        package_path = self.settings.workspace_root / "packages" / f"{build_id}.zip"
        package_manifest = VortexPackageBuilder(self.guard).build(
            staging,
            package_path,
            mod_name="NPV Studio Tutorial Women Hair Lineup",
            version="0.4.1-native-hair-lineup-test",
        )
        report = {
            "schema_version": 1,
            "build_id": build_id,
            "status": "vortex_hair_lineup_test_ready",
            "base_build": str(base),
            "build_root": str(build_root),
            "clones": clones,
            "native_resource_validation": {
                "archive": str(appearance_archive),
                "required_count": len(required_hair_resources),
                "found_count": len(found_hair_resources),
                "missing": missing_hair_resources,
            },
            "seamfix": {
                "component": "t0_000_pwa_base__full_seamfix",
                "installed_in_every_appearance": True,
                "enabled_by_default": True,
                "toggleable_in_appearance_creator": True,
            },
            "runtime_pruning": runtime_pruning,
            "processes": processes,
            "package": package_manifest,
            "game_writes": False,
            "vortex_writes": False,
        }
        report_path = self.guard.write_text(
            build_root / "reports" / "hair-lineup-build-report.json",
            json.dumps(report, indent=2) + "\n",
        )
        report["report_path"] = str(report_path)
        return report
