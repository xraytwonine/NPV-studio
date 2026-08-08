from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from npv_studio.core.paths import PathGuard
from npv_studio.data.loader import load_game_data
from npv_studio.domain.models import (
    AppSettings,
    BuildReport,
    CharacterConfig,
    ComponentSlot,
    StarterGarment,
)
from npv_studio.pipeline.dependencies import DependencyInspector
from npv_studio.pipeline.templates import TemplateRenderer


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_") or "npv"


class DryRunBuilder:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.guard = PathGuard(settings.game_root, settings.workspace_root)
        self.renderer = TemplateRenderer()

    def build(self, character: CharacterConfig) -> BuildReport:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        build_id = f"{_slug(character.namespace)}_{stamp}"
        build_root = self.guard.ensure_directory(self.settings.workspace_root / "builds" / build_id)
        source_root = self.guard.ensure_directory(build_root / "source")
        report_root = self.guard.ensure_directory(build_root / "reports")

        data = load_game_data(character.game_version)
        slots = [ComponentSlot.model_validate(slot) for slot in data["component_slots"]]
        starter_data = data["starter_outfit"]
        starter_garments = [
            StarterGarment.model_validate(garment)
            for garment in starter_data["body_frames"][character.body_frame.value]
        ]
        dependencies = DependencyInspector(self.settings, self.guard).inspect()

        generated: list[Path] = []
        character_path = self.guard.write_text(
            build_root / "character.json",
            json.dumps(character.model_dump(mode="json"), indent=2) + "\n",
        )
        generated.append(character_path)

        blender_request = {
            "schema_version": 1,
            "status": "request_only_alpha",
            "body_frame": character.body_frame.value,
            "morphs": character.head.model_dump(),
            "morph_name_encoding": data["morph_name_encoding"],
            "output_namespace": character.namespace,
        }
        blender_path = self.guard.write_text(
            source_root / "raw" / character.namespace / "head" / "blender_request.json",
            json.dumps(blender_request, indent=2) + "\n",
        )
        generated.append(blender_path)

        component_plan = {
            "schema_version": 1,
            "status": "template_resolution_required",
            "base_body": character.output.base_body,
            "appearances": [
                *(
                    [
                        {
                            "name": character.output.appearance_name,
                            "kind": "starter_outfit",
                            "initially_visible_components": [
                                garment.component_name for garment in starter_garments
                            ],
                        }
                    ]
                    if character.output.starter_outfit
                    else []
                ),
                *(
                    [
                        {
                            "name": character.output.base_body_appearance_name,
                            "kind": "base_body",
                            "initially_visible_components": [],
                        }
                    ]
                    if character.output.base_body
                    else []
                ),
            ],
            "starter_outfit": {
                "enabled": character.output.starter_outfit,
                "default_spawn_appearance": (
                    character.output.appearance_name
                    if character.output.starter_outfit
                    else character.output.base_body_appearance_name
                ),
                "mapping_status": starter_data["status"],
                "source_note": starter_data["source_note"],
                "components": [
                    garment.model_dump(mode="json") for garment in starter_garments
                ],
            },
            "permanent_components": [
                "body",
                "arms",
                "hands",
                "feet",
                "generated_head",
                "eyes",
                "teeth",
                "hair",
                "facial_details",
                "rig",
                "facial_animation",
            ],
            "editable_slots": [slot.model_dump(mode="json") for slot in slots],
        }
        plan_path = self.guard.write_text(
            source_root / "archive" / character.namespace / "component_plan.json",
            json.dumps(component_plan, indent=2) + "\n",
        )
        generated.append(plan_path)

        appearance_names = []
        if character.output.starter_outfit:
            appearance_names.append(character.output.appearance_name)
        if character.output.base_body:
            appearance_names.append(character.output.base_body_appearance_name)
        lua = self.renderer.render(
            "amm_entity.lua.j2",
            modder="NPV Studio user",
            unique_identifier=character.namespace,
            display_name=character.name,
            entity_path=f"npv_studio\\{character.namespace}\\{character.namespace}.ent",
            appearance_names=appearance_names,
        )
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
            / f"{character.namespace}.lua",
            lua,
        )
        generated.append(lua_path)

        distribution_plan = {
            "schema_version": 1,
            "status": "awaiting_compiled_game_resources",
            "target": character.output.package_target,
            "installation_owner": "Vortex",
            "direct_game_writes": False,
            "generated_archive_layout": {
                "archive/pc/mod": ["<namespace>.archive", "<namespace>.xl (optional)"],
                "bin/x64/plugins/cyber_engine_tweaks/mods/AppearanceMenuMod/Collabs/Custom Entities": [
                    "<namespace>.lua"
                ],
                "r6/tweaks/<namespace>": ["<namespace>.yaml (optional Photo Mode support)"],
            },
            "output_directory": str(self.settings.workspace_root / "packages"),
            "note": "The package builder will create a ZIP only after real compiled resources exist.",
        }
        distribution_path = self.guard.write_text(
            report_root / "distribution-plan.json",
            json.dumps(distribution_plan, indent=2) + "\n",
        )
        generated.append(distribution_path)

        warnings = [
            "Alpha output is a dry-run workspace and is not yet spawnable.",
            "No files were written to the Cyberpunk 2077 installation.",
            "Exact mesh, material, chunk-mask, rig, and morphtarget mappings remain provisional.",
            "The Vortex ZIP is intentionally withheld until a real WolvenKit archive exists.",
        ]
        if character.output.starter_outfit:
            warnings.append(
                "Starter outfit mesh paths are recorded but still require WolvenKit validation of "
                "resource existence, mesh appearance, materials, garment support, and chunk masks."
            )
        unavailable = [d.name for d in dependencies if not d.available]
        if unavailable:
            warnings.append("Unavailable optional build dependencies: " + ", ".join(unavailable))

        log_lines = [
            f"NPV Studio alpha build: {build_id}",
            f"Created (UTC): {datetime.now(timezone.utc).isoformat()}",
            f"Game source (READ ONLY): {self.settings.game_root}",
            f"Build output: {build_root}",
            "",
            "Dependencies:",
            *[
                f"- {dependency.name}: {'READY' if dependency.available else 'NOT FOUND'}"
                + (f" ({dependency.path})" if dependency.path else "")
                for dependency in dependencies
            ],
            "",
            "Warnings:",
            *[f"- {warning}" for warning in warnings],
        ]
        log_path = self.guard.write_text(
            report_root / "build.log",
            "\n".join(log_lines) + "\n",
        )
        generated.append(log_path)

        report = BuildReport(
            build_id=build_id,
            output_root=build_root,
            character=character,
            dependencies=dependencies,
            component_slots=slots,
            generated_files=generated,
            warnings=warnings,
            success=all(d.available for d in dependencies if d.required_for_dry_run),
        )
        report_path = self.guard.write_text(
            report_root / "build-report.json",
            json.dumps(report.as_json_data(), indent=2) + "\n",
        )
        report.generated_files.append(report_path)
        return report
