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
from npv_studio.domain.models import AppSettings, BodyFrame, CharacterConfig
from npv_studio.pipeline.appearance import (
    FEMALE_BODY_MESHES,
    FEMALE_BODY_TATTOOS,
    FEMALE_BIG_NIPPLES,
    FEMALE_NPC_BODY_MESH,
    FEMALE_SEAMFIX,
    SKIN_TONES,
    apply_female_npc_body_document,
    compile_female_appearance_document,
    female_hair_resource_paths,
    normalize_default_app_appearance,
    normalize_default_entity_appearance,
)
from npv_studio.pipeline.head import selected_female_head_components
from npv_studio.pipeline.package import VortexPackageBuilder
from npv_studio.pipeline.runtime_resources import prune_female_runtime_resources


SOURCE_APP_PATH = "tutorial\\npv\\your_female_character\\_your_female_character.app"
APPEARANCE_NAMES = ("tutorial_woman_casual", "tutorial_woman_business")
FINAL_APPEARANCE_NAMES = ("default",)
PLAYER_DEFORMATION_RIG = (
    "base\\characters\\entities\\player\\deformations_rigs_wa\\"
    "player_woman_base_deformations.rig"
)
PLAYER_DEFORMATION_GRAPH = (
    "base\\characters\\entities\\player\\deformations_rigs_wa\\"
    "player_woman_base_deformations.animgraph"
)
BODY_TEST_PROFILES: dict[str, dict[str, Any]] = {
    "dual_body": {
        "display_name": "Valkyrie Dual Body 04",
        "slug": "valkyrie_dual_body_04",
        "hairstyle": 4,
        "skin_tone": 5,
        "chest": "big",
        "game_resources": (
            FEMALE_BODY_MESHES["small"],
            FEMALE_BODY_MESHES["big"],
            FEMALE_BODY_TATTOOS["default"][3],
            FEMALE_BODY_TATTOOS["big"][3],
        ),
        "apply_npc_body": False,
        "player_deformation": False,
        "remove_local_arms": False,
        "remove_local_textures": False,
        "mod_name": "NPV Studio Valkyrie Dual Body Hair 04 Test",
        "version": "0.6.0-dual-body-test",
        "status": "vortex_dual_body_test_ready",
        "limitations": (
            "AMM does not switch related components as a group: disable t0_body before enabling t0_body_nude_large.",
            "For body tattoo 03, switch the clothing-safe and nude-large tattoo components at the same time as the torso.",
            "The clothing-safe torso is enabled by default; the nude-large torso is packaged but disabled.",
        ),
    },
    "npc_body": {
        "display_name": "Valkyrie NPC Body 04",
        "slug": "valkyrie_npc_body_04",
        "hairstyle": 4,
        "skin_tone": 5,
        "chest": "default",
        "game_resources": (FEMALE_NPC_BODY_MESH,),
        "apply_npc_body": True,
        "player_deformation": False,
        "remove_local_arms": True,
        "remove_local_textures": True,
        "mod_name": "NPV Studio Valkyrie NPC Body Hair 04 Test",
        "version": "0.5.0-npc-body-hair04-test",
        "status": "vortex_npc_body_test_ready",
        "limitations": (
            "This isolates Triad's vanilla NPC body mesh but does not include Triad's restricted deformation rig or graph.",
            "The NPC body uses the verified 03_ca_senna_naked appearance; Valkyrie's player-only amber tone is intentionally not used.",
        ),
    },
    "player_big_deformation": {
        "display_name": "Valkyrie Player Deform Big 04",
        "slug": "valkyrie_player_deform_big_04",
        "hairstyle": 4,
        "skin_tone": 5,
        "chest": "big",
        "game_resources": (
            FEMALE_BODY_MESHES["small"],
            FEMALE_BODY_MESHES["big"],
            FEMALE_BODY_TATTOOS["default"][3],
            FEMALE_BODY_TATTOOS["big"][3],
            PLAYER_DEFORMATION_RIG,
            PLAYER_DEFORMATION_GRAPH,
        ),
        "apply_npc_body": False,
        "player_deformation": True,
        "remove_local_arms": False,
        "remove_local_textures": False,
        "mod_name": "NPV Studio Valkyrie Player Deformation Big Hair 04 Test",
        "version": "0.5.1-player-deform-big-test",
        "status": "vortex_player_deformation_big_test_ready",
        "limitations": (
            "The vanilla player deformation graph may expect player-only runtime inputs; its NPC behavior requires in-game validation.",
            "The standalone big-breast nipple overlay is intentionally omitted for this test.",
            "The large player body supports the base 03_ca_senna appearance but not Valkyrie's amber sub-tone.",
        ),
    },
}


class NpcBodyTestBuildError(RuntimeError):
    """Raised when the isolated vanilla-NPC-body test cannot be built."""


def _require_success(stage: str, result: ProcessResult) -> None:
    if result.returncode != 0:
        raise NpcBodyTestBuildError(
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


def _amm_lua(
    entity_path: str,
    *,
    display_name: str,
    unique_identifier: str,
    appearance_names: tuple[str, ...] = APPEARANCE_NAMES,
) -> str:
    lua_path = entity_path.replace("\\", "\\\\")
    appearances = ",\n".join(f'    "{name}"' for name in appearance_names)
    return f'''return {{
  modder = "NPV Studio",
  unique_identifier = "{unique_identifier}",
  entity_info = {{
    name = "{display_name}",
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


def _prune_replaced_local_body_files(
    guard: PathGuard,
    archive_root: Path,
    *,
    remove_local_body: bool,
    remove_arms: bool,
    remove_textures: bool,
) -> dict[str, Any]:
    body_root = guard.assert_write_path(
        archive_root / "tutorial" / "npv" / "your_female_character" / "body"
    )
    targets = [body_root / "t0_000_pwa_base__full.mesh"] if remove_local_body else []
    if remove_arms:
        targets.extend(
            (
                body_root / "a0_000_pwa_base_hq__l.mesh",
                body_root / "a0_000_pwa_base_hq__r.mesh",
            )
        )
    texture_root = body_root / "textures"
    if remove_textures and texture_root.is_dir():
        targets.extend(path for path in texture_root.rglob("*") if path.is_file())

    removed: list[dict[str, Any]] = []
    for path in targets:
        if not path.is_file():
            continue
        size = path.stat().st_size
        removed.append(
            {
                "path": str(path.relative_to(archive_root)),
                "bytes": size,
            }
        )
        path.unlink()
    if texture_root.is_dir() and not any(texture_root.iterdir()):
        texture_root.rmdir()
    return {
        "files": len(removed),
        "bytes": sum(item["bytes"] for item in removed),
        "removed_files": removed,
    }


def _retarget_player_deformation_controller(document: dict[str, Any]) -> dict[str, Any]:
    updates = 0

    def walk(node: Any) -> None:
        nonlocal updates
        if isinstance(node, dict):
            name = node.get("name")
            component_name = name.get("$value") if isinstance(name, dict) else None
            if node.get("$type") == "entAnimatedComponent" and component_name == "deformations":
                rig_path = (node.get("rig") or {}).get("DepotPath")
                graph_path = (node.get("graph") or {}).get("DepotPath")
                if not isinstance(rig_path, dict) or "$value" not in rig_path:
                    raise NpcBodyTestBuildError("Deformation component has no editable rig path")
                if not isinstance(graph_path, dict) or "$value" not in graph_path:
                    raise NpcBodyTestBuildError("Deformation component has no editable graph path")
                rig_path["$value"] = PLAYER_DEFORMATION_RIG
                rig_path["$storage"] = "string"
                graph_path["$value"] = PLAYER_DEFORMATION_GRAPH
                graph_path["$storage"] = "string"
                updates += 1
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(document)
    if updates == 0:
        raise NpcBodyTestBuildError("Entity contains no editable deformations component")
    return {
        "component": "deformations",
        "rig": PLAYER_DEFORMATION_RIG,
        "graph": PLAYER_DEFORMATION_GRAPH,
        "updates": updates,
    }


class NpcBodyTestBuilder:
    """Build one hair-04 character using a controlled body/deformation profile."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        execute: bool = False,
        profile: str = "npc_body",
    ) -> None:
        if profile not in BODY_TEST_PROFILES:
            raise ValueError(f"Unknown body-test profile: {profile}")
        self.settings = settings
        self.profile_name = profile
        self.profile = BODY_TEST_PROFILES[profile]
        self.guard = PathGuard(settings.game_root, settings.workspace_root)
        self.runner = ExternalToolRunner(self.guard, enabled=execute)

    def build(
        self,
        base_build: Path,
        *,
        character: CharacterConfig | None = None,
        final: bool = False,
        package_output: bool = True,
    ) -> dict[str, Any]:
        if not self.runner.enabled:
            raise NpcBodyTestBuildError("NPC body generation requires the explicit --execute flag")
        wolvenkit = self.settings.wolvenkit_executable
        if wolvenkit is None or not wolvenkit.is_file():
            raise NpcBodyTestBuildError("A valid WolvenKit CLI executable is required")

        base = Path(base_build).resolve(strict=True)
        if not is_within(base, self.settings.workspace_root):
            raise NpcBodyTestBuildError("The verified base build must be inside the workspace")
        base_source = base / "source" if (base / "source").is_dir() else base
        original_root = base_source / "archive" / "tutorial" / "npv" / "your_female_character"
        original_app = original_root / "_your_female_character.app"
        original_ent = original_root / "_your_female_character.ent"
        if not original_app.is_file() or not original_ent.is_file():
            raise NpcBodyTestBuildError("The base build has no tutorial woman app/entity")

        report_root = base if (base / "reports").is_dir() else base.parent
        head_report_path = report_root / "reports" / "head-build-report.json"
        head_report = json.loads(head_report_path.read_text(encoding="utf-8"))
        if character is None:
            character_data = deepcopy(head_report["character"])
            display_name = str(self.profile["display_name"])
            slug = str(self.profile["slug"])
            hairstyle = int(self.profile["hairstyle"])
            skin_tone = int(self.profile["skin_tone"])
            character_data["name"] = display_name
            character_data["namespace"] = slug
            character_data["appearance"]["hairstyle"] = hairstyle
            character_data["appearance"]["skin_tone"] = skin_tone
            character_data["appearance"]["chest"] = str(self.profile["chest"])
            character_data["appearance"]["nipples"] = 0
            character = CharacterConfig.model_validate(character_data)
        else:
            if character.body_frame is not BodyFrame.FEMALE:
                raise NpcBodyTestBuildError("The dual-body finalizer supports the feminine frame only")
            display_name = character.name
            slug = character.namespace
            hairstyle = character.appearance.hairstyle
            skin_tone = character.appearance.skin_tone

        template_project = Path(head_report["template_project"]).resolve(strict=True)
        clean_app = (
            template_project
            / "source"
            / "archive"
            / "tutorial"
            / "npv"
            / "your_female_character"
            / "_your_female_character.app"
        )
        if not clean_app.is_file():
            raise NpcBodyTestBuildError(f"The clean template app is missing: {clean_app}")

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        build_id = f"{slug}_{stamp}"
        build_root = self.guard.assert_write_path(
            self.settings.workspace_root
            / "integration"
            / ("final_builds" if final else "npc_body_tests")
            / build_id
        )
        if build_root.exists():
            raise NpcBodyTestBuildError(f"Refusing to overwrite existing build: {build_root}")
        source_root = build_root / "source"
        shutil.copytree(base_source, source_root)
        resource_root = source_root / "archive" / "tutorial" / "npv" / "your_female_character"
        source_app = resource_root / "_your_female_character.app"
        source_ent = resource_root / "_your_female_character.ent"

        profile_resources = set(self.profile["game_resources"])
        if final:
            profile_resources = {
                FEMALE_BODY_MESHES["small"],
                FEMALE_BODY_MESHES["big"],
                FEMALE_SEAMFIX,
            }
            tattoo = character.appearance.body_tattoos
            if tattoo:
                try:
                    profile_resources.update(
                        (FEMALE_BODY_TATTOOS["default"][tattoo], FEMALE_BODY_TATTOOS["big"][tattoo])
                    )
                except KeyError as exc:
                    raise NpcBodyTestBuildError(
                        f"No verified dual-body tattoo mapping for selection {tattoo}"
                    ) from exc
            nipples = character.appearance.nipples
            if nipples:
                try:
                    profile_resources.add(FEMALE_BIG_NIPPLES[nipples])
                except KeyError as exc:
                    raise NpcBodyTestBuildError(
                        f"No verified large-body nipple mapping for selection {nipples}"
                    ) from exc
        required_resources = sorted({*female_hair_resource_paths(hairstyle), *profile_resources})
        appearance_archive = self.guard.assert_game_read_path(
            self.settings.game_root / "archive" / "pc" / "content" / "basegame_4_appearance.archive"
        )
        resource_regex = "^(?:" + "|".join(re.escape(path) for path in required_resources) + ")$"
        processes: dict[str, Any] = {}
        validation = self.runner.run(
            wolvenkit,
            ["archiveinfo", str(appearance_archive), "--list", "--regex", resource_regex],
            build_root,
        )
        processes["validate_game_resources"] = _process_data(validation)
        _require_success("Game resource validation", validation)
        found = {
            line.strip().casefold()
            for line in validation.stdout.splitlines()
            if line.strip().casefold().startswith("base\\")
        }
        missing = [path for path in required_resources if path.casefold() not in found]
        if missing:
            raise NpcBodyTestBuildError("Missing game resources: " + ", ".join(missing))

        json_root = self.guard.ensure_directory(build_root / "resource_json")
        app_source_json_root = self.guard.ensure_directory(json_root / "source_app")
        app_serialize = self.runner.run(
            wolvenkit,
            ["convert", "serialize", str(clean_app), "--outpath", str(app_source_json_root)],
            build_root,
        )
        processes["serialize_clean_app"] = _process_data(app_serialize)
        _require_success("Clean app serialization", app_serialize)
        clean_app_json = app_source_json_root / "_your_female_character.app.json"
        app_document = json.loads(clean_app_json.read_text(encoding="utf-8"))
        appearance_report = compile_female_appearance_document(app_document, character)
        default_app_report = normalize_default_app_appearance(app_document) if final else None
        body_profile_report: dict[str, Any] = {
            "profile": self.profile_name,
            "body_mesh": FEMALE_BODY_MESHES[str(self.profile["chest"])],
            "skin_base": SKIN_TONES[skin_tone],
        }
        if bool(self.profile["apply_npc_body"]):
            npc_body_report = apply_female_npc_body_document(
                app_document, skin_base=SKIN_TONES[skin_tone]
            )
            body_profile_report.update(npc_body_report)
            for appearance_name, changes in npc_body_report["changed_by_appearance"].items():
                appearance_report["changed_by_appearance"][appearance_name].update(changes)
            appearance_report["warnings"] = [
                warning
                for warning in appearance_report["warnings"]
                if "prepared tutorial NPV body" not in warning
                and "seam-fix overlay" not in warning
            ]
            appearance_report["warnings"].extend(
                [
                    "The vanilla NPC woman full body includes its arms; separate player arms were removed.",
                    "The player seam-fix overlay was removed because it is not part of the NPC full-body architecture.",
                ]
            )

        depot_root = (
            f"tutorial\\npv\\npv_studio\\{slug}"
            if final
            else f"tutorial\\npv\\body_tests\\{slug}"
        )
        app_depot_path = f"{depot_root}\\{slug}.app"
        ent_depot_path = f"{depot_root}\\{slug}.ent"
        clone_root = source_root / "archive" / Path(*depot_root.split("\\"))
        clone_root.mkdir(parents=True, exist_ok=True)
        app_json = self.guard.write_text(
            json_root / f"{slug}.app.json", json.dumps(app_document, indent=2) + "\n"
        )
        app_deserialize = self.runner.run(
            wolvenkit,
            ["convert", "deserialize", str(app_json), "--outpath", str(clone_root)],
            build_root,
        )
        processes["deserialize_app"] = _process_data(app_deserialize)
        _require_success("NPC body app deserialization", app_deserialize)
        clone_app = clone_root / f"{slug}.app"
        if not clone_app.is_file():
            raise NpcBodyTestBuildError(f"WolvenKit did not create {clone_app}")

        ent_json_root = self.guard.ensure_directory(json_root / "source_ent")
        ent_serialize = self.runner.run(
            wolvenkit,
            ["convert", "serialize", str(source_ent), "--outpath", str(ent_json_root)],
            build_root,
        )
        processes["serialize_source_ent"] = _process_data(ent_serialize)
        _require_success("Source entity serialization", ent_serialize)
        ent_document = json.loads(
            (ent_json_root / "_your_female_character.ent.json").read_text(encoding="utf-8")
        )
        deformation_report = None
        if bool(self.profile["player_deformation"]):
            deformation_report = _retarget_player_deformation_controller(ent_document)
        replacement_count = _replace_resource_path(
            ent_document, SOURCE_APP_PATH, app_depot_path
        )
        if replacement_count != len(APPEARANCE_NAMES):
            raise NpcBodyTestBuildError(
                f"Expected {len(APPEARANCE_NAMES)} entity app references; replaced {replacement_count}"
            )
        default_entity_report = (
            normalize_default_entity_appearance(ent_document) if final else None
        )
        ent_json = self.guard.write_text(
            json_root / f"{slug}.ent.json", json.dumps(ent_document, indent=2) + "\n"
        )
        ent_deserialize = self.runner.run(
            wolvenkit,
            ["convert", "deserialize", str(ent_json), "--outpath", str(clone_root)],
            build_root,
        )
        processes["deserialize_ent"] = _process_data(ent_deserialize)
        _require_success("NPC body entity deserialization", ent_deserialize)
        clone_ent = clone_root / f"{slug}.ent"
        if not clone_ent.is_file():
            raise NpcBodyTestBuildError(f"WolvenKit did not create {clone_ent}")

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
            / ("npv_studio" if final else "npv_studio_body_tests")
            / f"{slug}.lua",
            _amm_lua(
                ent_depot_path,
                display_name=display_name,
                unique_identifier=f"npv_studio_{slug}",
                appearance_names=FINAL_APPEARANCE_NAMES if final else APPEARANCE_NAMES,
            ),
        )

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
        replaced_body_pruning = _prune_replaced_local_body_files(
            self.guard,
            source_root / "archive",
            remove_local_body=bool(self.profile["apply_npc_body"]),
            remove_arms=bool(self.profile["remove_local_arms"]),
            remove_textures=bool(self.profile["remove_local_textures"]),
        )

        compiled_root = self.guard.ensure_directory(build_root / "compiled")
        pack_result = self.runner.run(
            wolvenkit,
            ["pack", str(source_root / "archive"), "--outpath", str(compiled_root)],
            build_root,
        )
        processes["pack"] = _process_data(pack_result)
        _require_success("NPC body archive pack", pack_result)
        archives = sorted(compiled_root.glob("*.archive"))
        if len(archives) != 1:
            raise NpcBodyTestBuildError(f"Expected one packed archive, found {len(archives)}")

        staging = self.guard.ensure_directory(build_root / "staging")
        archive_target = staging / "archive" / "pc" / "mod" / f"npv_studio_{slug}.archive"
        archive_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archives[0], archive_target)
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
            / ("npv_studio" if final else "npv_studio_body_tests")
            / lua_path.name
        )
        lua_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lua_path, lua_target)

        package_manifest = None
        if package_output:
            package_path = self.settings.workspace_root / "packages" / f"{build_id}.zip"
            package_manifest = VortexPackageBuilder(self.guard).build(
                staging,
                package_path,
                mod_name=(f"{character.name} NPV" if final else str(self.profile["mod_name"])),
                version=("1.0.0" if final else str(self.profile["version"])),
            )
        report = {
            "schema_version": 1,
            "build_id": build_id,
            "status": "spawnable_vortex_package_ready" if final else str(self.profile["status"]),
            "base_build": str(base),
            "build_root": str(build_root),
            "display_name": display_name,
            "character": character.model_dump(mode="json"),
            "entity_depot_path": ent_depot_path,
            "app_depot_path": app_depot_path,
            "appearance_names": list(
                FINAL_APPEARANCE_NAMES if final else APPEARANCE_NAMES
            ),
            "appearance": appearance_report,
            "default_appearance": {
                "app": default_app_report,
                "entity": default_entity_report,
            },
            "body_profile": body_profile_report,
            "deformation_controller": deformation_report,
            "resource_validation": {
                "archive": str(appearance_archive),
                "required": required_resources,
                "missing": missing,
            },
            "hashes": {"app": _sha256(clone_app), "ent": _sha256(clone_ent)},
            "runtime_pruning": runtime_pruning,
            "replaced_body_pruning": replaced_body_pruning,
            "processes": processes,
            "package": package_manifest,
            "limitations": (
                [
                    "For feminine NPVs, the selected torso starts enabled; normal and big "
                    "torso variants are always included as AMM toggles.",
                    "AMM torso, tattoo, and nipple overlays must be toggled as a matching set.",
                ]
                if final
                else list(self.profile["limitations"])
            ),
            "game_writes": False,
            "vortex_writes": False,
        }
        report_path = self.guard.write_text(
            build_root / "reports" / "npc-body-test-report.json",
            json.dumps(report, indent=2) + "\n",
        )
        report["report_path"] = str(report_path)
        return report
