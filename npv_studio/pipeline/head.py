from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from npv_studio.adapters.process import ExternalToolRunner, ProcessResult
from npv_studio.core.paths import PathGuard, is_within
from npv_studio.core.runtime import bundled_resource_root
from npv_studio.domain.models import AppSettings, BodyFrame, CharacterConfig
from npv_studio.pipeline.package import VortexPackageBuilder
from npv_studio.pipeline.body_assets import BodyAssetBuilder
from npv_studio.pipeline.appearance import (
    compile_female_appearance_document,
    compile_male_appearance_document,
    normalize_default_app_appearance,
    normalize_default_entity_appearance,
)
from npv_studio.pipeline.runtime_resources import (
    prune_female_runtime_resources,
    prune_male_runtime_resources,
)
from npv_studio.pipeline.creator_assets import (
    BEARD_MESHES,
    CYBERWARE,
    FACIAL_TATTOO_MESHES,
    PIERCINGS,
    earring_mesh_pair,
    head_mesh_pair,
)


PROJECT_ROOT = bundled_resource_root()
BLENDER_WORKER = PROJECT_ROOT / "blender" / "generate_head.py"


BASE_FEMALE_COMPONENTS = (
    ("h0_000_pwa_c__basehead", "h0_000_pwa__morphs"),
    ("heb_000_pwa_c__basehead", "heb_000_pwa__morphs"),
    ("he_000_pwa_c__basehead", "he_000_pwa__morphs"),
    ("ht_000_pwa_c__basehead", "ht_000_pwa__morphs"),
)

BASE_MALE_COMPONENTS = (
    ("h0_000_pma_c__basehead", "h0_000_pma__morphs"),
    ("heb_000_pma_c__basehead", "heb_000_pma__morphs"),
    ("he_000_pma_c__basehead", "he_000_pma__morphs"),
    ("ht_000_pma_c__basehead", "ht_000_pma__morphs"),
)


def _unique_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return list(dict.fromkeys(pairs))


class HeadBuildError(RuntimeError):
    """Raised when the real template-backed head workflow cannot be completed."""


def selected_female_head_components(character: CharacterConfig) -> list[tuple[str, str]]:
    if character.body_frame is not BodyFrame.FEMALE:
        raise HeadBuildError("The first real head worker currently supports the feminine frame only")
    selected = list(BASE_FEMALE_COMPONENTS)
    if character.appearance.cyberware:
        selected.append(head_mesh_pair(BodyFrame.FEMALE, CYBERWARE[character.appearance.cyberware]["mesh"]))
    if character.appearance.facial_scars:
        selected.append(head_mesh_pair(BodyFrame.FEMALE, "scars_01"))
    if character.appearance.facial_tattoos:
        selected.append(
            head_mesh_pair(
                BodyFrame.FEMALE,
                FACIAL_TATTOO_MESHES[character.appearance.facial_tattoos],
            )
        )
    if character.appearance.piercings:
        selected.extend(
            earring_mesh_pair(BodyFrame.FEMALE, number)
            for number, _chunk_mask in PIERCINGS[BodyFrame.FEMALE][character.appearance.piercings]
        )
    if character.appearance.eye_makeup:
        selected.append(
            (
                "hx_000_pwa_c__basehead_makeup_eyes_01",
                "hx_000_pwa__morphs_makeup_eyes_01",
            )
        )
    if character.appearance.cheek_makeup or character.appearance.blemishes:
        selected.append(head_mesh_pair(BodyFrame.FEMALE, "makeup_freckles_01"))
    if character.appearance.lip_makeup:
        selected.append(head_mesh_pair(BodyFrame.FEMALE, "makeup_lips_01"))
    return _unique_pairs(selected)


def selected_male_head_components(character: CharacterConfig) -> list[tuple[str, str]]:
    if character.body_frame is not BodyFrame.MALE:
        raise HeadBuildError("The masculine head worker requires the masculine frame")
    selected = list(BASE_MALE_COMPONENTS)
    if character.appearance.cyberware:
        selected.append(head_mesh_pair(BodyFrame.MALE, CYBERWARE[character.appearance.cyberware]["mesh"]))
    if character.appearance.facial_scars:
        selected.append(head_mesh_pair(BodyFrame.MALE, "scars_01"))
    if character.appearance.facial_tattoos:
        selected.append(
            head_mesh_pair(
                BodyFrame.MALE,
                FACIAL_TATTOO_MESHES[character.appearance.facial_tattoos],
            )
        )
    if character.appearance.piercings:
        selected.extend(
            earring_mesh_pair(BodyFrame.MALE, number)
            for number, _chunk_mask in PIERCINGS[BodyFrame.MALE][character.appearance.piercings]
        )
    if character.appearance.blemishes:
        selected.append(
            ("hx_000_pma_c__basehead_pimples_01", "hx_000_pma__morphs_pimples_01")
        )
    if character.appearance.lip_makeup:
        selected.append(
            (
                "hx_000_pma_c__basehead_makeup_lips_01",
                "hx_000_pma__morphs_makeup_lips_01",
            )
        )
    if character.appearance.eye_makeup:
        selected.append(head_mesh_pair(BodyFrame.MALE, "makeup_eyes_01"))
    if character.appearance.cheek_makeup:
        selected.append(head_mesh_pair(BodyFrame.MALE, "makeup_freckles_01"))
    if character.appearance.beard:
        for stem in BEARD_MESHES[character.appearance.beard]:
            if stem == "default":
                selected.append(
                    ("hb_000_pma_c__basehead", "hb_000_pma__morphs_default")
                )
            else:
                selected.append(
                    (
                        f"hb_000_pma_c__basehead_{stem}",
                        f"hb_000_pma__morphs_{stem}",
                    )
                )
    return _unique_pairs(selected)


def selected_head_components(character: CharacterConfig) -> list[tuple[str, str]]:
    if character.body_frame is BodyFrame.MALE:
        return selected_male_head_components(character)
    return selected_female_head_components(character)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_success(stage: str, result: ProcessResult) -> None:
    if result.returncode != 0:
        raise HeadBuildError(
            f"{stage} failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _require_output_marker(stage: str, result: ProcessResult, marker: str) -> None:
    _require_success(stage, result)
    if marker not in result.stdout:
        raise HeadBuildError(
            f"{stage} did not report its required success marker {marker!r}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _process_data(result: ProcessResult) -> dict[str, Any]:
    return {
        "command": list(result.command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


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


def _amm_lua(
    *,
    entity_path: str,
    display_name: str,
    namespace: str,
    appearance_names: tuple[str, ...] = (
        "tutorial_man_casual",
        "tutorial_man_business",
    ),
) -> str:
    lua_path = entity_path.replace("\\", "\\\\")
    appearances = ",\n".join(f'    "{name}"' for name in appearance_names)
    return f'''return {{
  modder = "NPV Studio",
  unique_identifier = "npv_studio_{namespace}",
  entity_info = {{
    name = "{display_name}",
    path = "{lua_path}",
    record = "Character.afterlife_merc_fast_melee_m_hard",
    type = "Character",
    customName = true
  }},
  appearances = {{
{appearances}
  }},
  attributes = {{}},
}}
'''


class HeadTestBuilder:
    """Runs the first real WolvenKit -> Blender -> WolvenKit vertical slice."""

    def __init__(self, settings: AppSettings, *, execute: bool = False) -> None:
        self.settings = settings
        self.guard = PathGuard(settings.game_root, settings.workspace_root)
        self.runner = ExternalToolRunner(self.guard, enabled=execute)

    def build(
        self,
        character: CharacterConfig,
        template_project: Path,
        *,
        package_output: bool = True,
        final: bool = False,
    ) -> dict[str, Any]:
        if not self.runner.enabled:
            raise HeadBuildError("Real head generation requires the explicit --execute flag")
        if self.settings.wolvenkit_executable is None or not self.settings.wolvenkit_executable.is_file():
            raise HeadBuildError("A valid WolvenKit CLI executable is required")
        if self.settings.blender_executable is None or not self.settings.blender_executable.is_file():
            raise HeadBuildError("A valid Blender executable is required")

        template = Path(template_project).resolve(strict=True)
        if not is_within(template, self.settings.workspace_root):
            raise HeadBuildError("Template project must be inside the configured workspace")
        template_source = template / "source"
        if not template_source.is_dir():
            raise HeadBuildError(f"Template project has no source directory: {template_source}")

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        build_id = f"{character.namespace}_head_{stamp}"
        build_root = self.guard.assert_write_path(
            self.settings.workspace_root / "integration" / "head_tests" / build_id
        )
        if build_root.exists():
            raise HeadBuildError(f"Refusing to overwrite an existing head build: {build_root}")
        source_root = build_root / "source"
        shutil.copytree(template_source, source_root)

        character_directory = (
            "your_male_character"
            if character.body_frame is BodyFrame.MALE
            else "your_female_character"
        )
        app_basename = (
            "_your_male_character"
            if character.body_frame is BodyFrame.MALE
            else "_your_female_character"
        )
        archive_head = source_root / "archive" / "tutorial" / "npv" / character_directory / "head"
        raw_head = source_root / "raw" / "tutorial" / "npv" / character_directory / "head"
        morph_root = archive_head / "morphtargets"
        raw_morph_root = raw_head / "morphtargets"
        raw_morph_root.mkdir(parents=True, exist_ok=True)
        blend_file = raw_head / "head_import.blend"
        for required in (archive_head, morph_root, blend_file, BLENDER_WORKER):
            if not required.exists():
                raise HeadBuildError(f"Required head resource is missing: {required}")

        selected = selected_head_components(character)
        morph_sources: list[Path] = []
        mesh_sources: list[Path] = []
        for mesh_stem, morph_stem in selected:
            mesh = archive_head / f"{mesh_stem}.mesh"
            morph = morph_root / f"{morph_stem}.morphtarget"
            if not mesh.is_file() or not morph.is_file():
                raise HeadBuildError(f"Selected head mapping is missing: {mesh} / {morph}")
            mesh_sources.append(mesh)
            morph_sources.append(morph)
        original_mesh_hashes = {path.name: _sha256(path) for path in mesh_sources}

        processes: dict[str, Any] = {}
        export_result = self.runner.run(
            self.settings.wolvenkit_executable,
            [
                "export",
                *[str(path) for path in morph_sources],
                "--outpath",
                str(raw_morph_root),
                "--gamepath",
                str(self.guard.assert_game_read_path(self.settings.game_root)),
                "--verbosity",
                "Normal",
            ],
            build_root,
        )
        processes["wolvenkit_export"] = _process_data(export_result)
        _require_success("WolvenKit morphtarget export", export_result)
        expected_morph_glbs = [raw_morph_root / f"{stem}.morphtarget.glb" for _, stem in selected]
        missing_exports = [str(path) for path in expected_morph_glbs if not path.is_file()]
        if missing_exports:
            raise HeadBuildError("Missing exported morphtarget GLBs: " + ", ".join(missing_exports))

        request = {
            "schema_version": 1,
            "body_frame": character.body_frame.value,
            "morphs": character.head.model_dump(),
            "expected_exports": [mesh_stem for mesh_stem, _ in selected],
            "selected_components": [
                {"mesh": f"{mesh}.mesh", "morphtarget": f"{morph}.morphtarget"}
                for mesh, morph in selected
            ],
        }
        request_path = self.guard.write_text(
            build_root / "reports" / "blender-request.json",
            json.dumps(request, indent=2) + "\n",
        )
        blender_result = self.runner.run(
            self.settings.blender_executable,
            [
                "--background",
                str(blend_file),
                "--python",
                str(BLENDER_WORKER),
                "--",
                str(request_path),
            ],
            build_root,
        )
        processes["blender"] = _process_data(blender_result)
        _require_success("Blender head generation", blender_result)
        blender_report_path = request_path.with_name("blender-result.json")
        blender_report = json.loads(blender_report_path.read_text(encoding="utf-8"))
        if not blender_report["success"]:
            raise HeadBuildError(f"Blender report failed: {blender_report.get('error')}")

        mesh_glbs = [raw_head / f"{mesh_stem}.glb" for mesh_stem, _ in selected]
        missing_mesh_glbs = [str(path) for path in mesh_glbs if not path.is_file()]
        if missing_mesh_glbs:
            raise HeadBuildError("Missing Blender mesh GLBs: " + ", ".join(missing_mesh_glbs))
        import_result = self.runner.run(
            self.settings.wolvenkit_executable,
            [
                "import",
                *[str(path) for path in mesh_glbs],
                "--outpath",
                str(archive_head),
                "--keep",
                "--verbosity",
                "Normal",
            ],
            build_root,
        )
        processes["wolvenkit_import"] = _process_data(import_result)
        _require_success("WolvenKit mesh import", import_result)

        rebuilt_mesh_hashes = {path.name: _sha256(path) for path in mesh_sources}
        unchanged = [name for name, digest in rebuilt_mesh_hashes.items() if digest == original_mesh_hashes[name]]
        if unchanged:
            raise HeadBuildError("WolvenKit did not modify expected meshes: " + ", ".join(unchanged))
        warnings: list[str] = []
        if "Garment support is enabled" in import_result.stdout:
            warnings.append(
                "WolvenKit skipped garment-support parameters for the generated head meshes; "
                "the head-test package requires in-game visual validation before this can be accepted."
            )

        # Body overlays with creator morphs (female scars, penis size and the
        # matching penile pubic-hair mesh) are baked into static local meshes
        # before the app document references them.
        body_assets = BodyAssetBuilder(self.settings, execute=True).build(
            build_root, source_root, character
        )
        processes["body_assets"] = body_assets

        app_path = (
            source_root
            / "archive"
            / "tutorial"
            / "npv"
            / character_directory
            / f"{app_basename}.app"
        )
        appearance_json_root = build_root / "appearance_json"
        appearance_json_root.mkdir(parents=True, exist_ok=True)
        original_app_hash = _sha256(app_path)
        serialize_result = self.runner.run(
            self.settings.wolvenkit_executable,
            ["convert", "serialize", str(app_path), "--outpath", str(appearance_json_root)],
            build_root,
        )
        processes["wolvenkit_serialize_app"] = _process_data(serialize_result)
        _require_output_marker("WolvenKit app serialization", serialize_result, "Saved ")
        app_json_path = appearance_json_root / f"{app_basename}.app.json"
        if not app_json_path.is_file():
            raise HeadBuildError(f"WolvenKit did not create app JSON: {app_json_path}")
        app_document = json.loads(app_json_path.read_text(encoding="utf-8"))
        appearance_report = (
            compile_male_appearance_document(app_document, character)
            if character.body_frame is BodyFrame.MALE
            else compile_female_appearance_document(app_document, character)
        )
        default_appearance_report = (
            normalize_default_app_appearance(app_document) if final else None
        )
        self.guard.write_text(app_json_path, json.dumps(app_document, indent=2) + "\n")
        deserialize_result = self.runner.run(
            self.settings.wolvenkit_executable,
            ["convert", "deserialize", str(app_json_path), "--outpath", str(app_path.parent)],
            build_root,
        )
        processes["wolvenkit_deserialize_app"] = _process_data(deserialize_result)
        _require_output_marker(
            "WolvenKit app deserialization",
            deserialize_result,
            f"Imported {app_basename}.app.json",
        )
        if not app_path.is_file():
            raise HeadBuildError(f"WolvenKit did not rebuild the app resource: {app_path}")
        rebuilt_app_hash = _sha256(app_path)
        if rebuilt_app_hash == original_app_hash:
            raise HeadBuildError("WolvenKit reported success but did not change the app resource")

        unique_lua: Path | None = None
        unique_registration: dict[str, Any] | None = None
        if character.body_frame is BodyFrame.MALE:
            original_ent = app_path.with_name("_your_male_character.ent")
            if not original_ent.is_file():
                raise HeadBuildError(f"Masculine template entity is missing: {original_ent}")
            entity_json_root = self.guard.ensure_directory(build_root / "entity_json")
            serialize_ent = self.runner.run(
                self.settings.wolvenkit_executable,
                ["convert", "serialize", str(original_ent), "--outpath", str(entity_json_root)],
                build_root,
            )
            processes["wolvenkit_serialize_ent"] = _process_data(serialize_ent)
            _require_success("WolvenKit entity serialization", serialize_ent)
            original_ent_json = entity_json_root / "_your_male_character.ent.json"
            if not original_ent_json.is_file():
                raise HeadBuildError(f"WolvenKit did not create entity JSON: {original_ent_json}")

            depot_directory = f"tutorial\\npv\\npv_studio\\{character.namespace}"
            app_depot_path = f"{depot_directory}\\{character.namespace}.app"
            ent_depot_path = f"{depot_directory}\\{character.namespace}.ent"
            clone_root = source_root / "archive" / Path(*depot_directory.split("\\"))
            clone_root.mkdir(parents=True, exist_ok=True)
            unique_json_root = self.guard.ensure_directory(build_root / "unique_json")
            unique_app_json = self.guard.write_text(
                unique_json_root / f"{character.namespace}.app.json",
                json.dumps(app_document, indent=2) + "\n",
            )
            deserialize_unique_app = self.runner.run(
                self.settings.wolvenkit_executable,
                ["convert", "deserialize", str(unique_app_json), "--outpath", str(clone_root)],
                build_root,
            )
            processes["wolvenkit_deserialize_unique_app"] = _process_data(deserialize_unique_app)
            _require_success("WolvenKit unique app deserialization", deserialize_unique_app)
            unique_app = clone_root / f"{character.namespace}.app"
            if not unique_app.is_file():
                raise HeadBuildError(f"WolvenKit did not create unique app: {unique_app}")

            ent_document = json.loads(original_ent_json.read_text(encoding="utf-8"))
            original_app_depot_path = (
                "tutorial\\npv\\your_male_character\\_your_male_character.app"
            )
            replacements = _replace_resource_path(
                ent_document, original_app_depot_path, app_depot_path
            )
            if replacements != 2:
                raise HeadBuildError(
                    f"Unique Vincent entity expected 2 app references; replaced {replacements}"
                )
            default_entity_report = (
                normalize_default_entity_appearance(ent_document) if final else None
            )
            unique_ent_json = self.guard.write_text(
                unique_json_root / f"{character.namespace}.ent.json",
                json.dumps(ent_document, indent=2) + "\n",
            )
            deserialize_unique_ent = self.runner.run(
                self.settings.wolvenkit_executable,
                ["convert", "deserialize", str(unique_ent_json), "--outpath", str(clone_root)],
                build_root,
            )
            processes["wolvenkit_deserialize_unique_ent"] = _process_data(deserialize_unique_ent)
            _require_success("WolvenKit unique entity deserialization", deserialize_unique_ent)
            unique_ent = clone_root / f"{character.namespace}.ent"
            if not unique_ent.is_file():
                raise HeadBuildError(f"WolvenKit did not create unique entity: {unique_ent}")

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
                / "tutorial_custom_male_character.lua"
            )
            if original_lua.is_file():
                original_lua.unlink()
            unique_lua = self.guard.write_text(
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
                / "npv_studio"
                / f"{character.namespace}.lua",
                _amm_lua(
                    entity_path=ent_depot_path,
                    display_name=character.name,
                    namespace=character.namespace,
                    appearance_names=("default",) if final else (
                        "tutorial_man_casual",
                        "tutorial_man_business",
                    ),
                ),
            )
            app_path.unlink()
            original_ent.unlink()
            unique_registration = {
                "mode": "unique_entity",
                "display_name": character.name,
                "unique_identifier": f"npv_studio_{character.namespace}",
                "entity_depot_path": ent_depot_path,
                "app_depot_path": app_depot_path,
                "app_sha256": _sha256(unique_app),
                "ent_sha256": _sha256(unique_ent),
                "default_appearance": default_entity_report,
            }

        prune = (
            prune_male_runtime_resources
            if character.body_frame is BodyFrame.MALE
            else prune_female_runtime_resources
        )
        runtime_pruning = prune(
            self.guard, source_root / "archive", (mesh_stem for mesh_stem, _ in selected)
        )

        compiled_root = self.guard.ensure_directory(build_root / "compiled")
        pack_result = self.runner.run(
            self.settings.wolvenkit_executable,
            ["pack", str(source_root / "archive"), "--outpath", str(compiled_root)],
            build_root,
        )
        processes["wolvenkit_pack"] = _process_data(pack_result)
        _require_success("WolvenKit archive pack", pack_result)
        archives = sorted(compiled_root.glob("*.archive"))
        if len(archives) != 1:
            raise HeadBuildError(f"Expected one packed archive, found {len(archives)}")

        staging = build_root / "staging"
        archive_target = staging / "archive" / "pc" / "mod" / f"{character.namespace}_head_test.archive"
        archive_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archives[0], archive_target)
        source_lua = unique_lua or (
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
            / (
                "tutorial_custom_male_character.lua"
                if character.body_frame is BodyFrame.MALE
                else "tutorial_custom_female_character.lua"
            )
        )
        lua_target = (
            staging
            / "bin"
            / "x64"
            / "plugins"
            / "cyber_engine_tweaks"
            / "mods"
            / "AppearanceMenuMod"
            / "Collabs"
            / "Custom Entities"
            / ("npv_studio" if unique_lua is not None else "tutorial")
            / (
                f"{character.namespace}.lua"
                if unique_lua is not None
                else "tutorial_custom_female_character.lua"
            )
        )
        # Masculine builds stage their generated unique AMM record; the feminine
        # compatibility workflow continues to stage the tutorial registration.
        self.guard.write_text(lua_target, source_lua.read_text(encoding="utf-8"))

        package_manifest = None
        if package_output:
            package_path = self.settings.workspace_root / "packages" / f"{build_id}.zip"
            package_manifest = VortexPackageBuilder(self.guard).build(
                staging,
                package_path,
                mod_name=(
                    f"{character.name} NPV Alpha"
                    if unique_lua is not None
                    else f"{character.name} Appearance Test (Tutorial AMM Registration)"
                ),
                version="0.4.0-masculine-alpha" if unique_lua is not None else "0.3.0-appearance-test",
            )
        report = {
            "schema_version": 1,
            "build_id": build_id,
            "status": "appearance_test_package_ready",
            "character": character.model_dump(mode="json"),
            "template_project": str(template),
            "build_root": str(build_root),
            "selected_components": request["selected_components"],
            "original_mesh_hashes": original_mesh_hashes,
            "rebuilt_mesh_hashes": rebuilt_mesh_hashes,
            "blender": blender_report,
            "appearance": appearance_report,
            "default_appearance": default_appearance_report,
            "runtime_pruning": runtime_pruning,
            "app_hashes": {"original": original_app_hash, "rebuilt": rebuilt_app_hash},
            "processes": processes,
            "amm_registration": unique_registration or {
                "mode": "template_compatibility",
                "display_name": "Tutorial Man" if character.body_frame is BodyFrame.MALE else "Tutorial Woman",
                "unique_identifier": (
                    "tutorial_male_character"
                    if character.body_frame is BodyFrame.MALE
                    else "tutorial_female_character"
                ),
                "reason": "The head test reuses the tutorial entity path and its existing AMM database row.",
            },
            "warnings": warnings,
            "package": package_manifest,
            "game_writes": False,
            "vortex_writes": False,
        }
        report_path = self.guard.write_text(
            build_root / "reports" / "head-build-report.json",
            json.dumps(report, indent=2) + "\n",
        )
        report["report_path"] = str(report_path)
        return report
