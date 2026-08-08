from __future__ import annotations

import argparse
import json
from pathlib import Path

from npv_studio.core.settings import DEFAULT_SETTINGS_PATH, load_settings
from npv_studio.domain.models import BodyFrame, CharacterConfig, HeadShape, VoiceTone
from npv_studio.pipeline.builder import DryRunBuilder
from npv_studio.pipeline.dependencies import DependencyInspector
from npv_studio.pipeline.package import PackageInspector, VortexPackageBuilder
from npv_studio.pipeline.intake import (
    analyze_character_source,
    character_draft_from_source,
    load_character_config,
)
from npv_studio.pipeline.final_build import FinalBuildBuilder
from npv_studio.pipeline.head import HeadTestBuilder
from npv_studio.pipeline.hair_lineup import HairLineupBuilder
from npv_studio.pipeline.npc_body_test import NpcBodyTestBuilder
from npv_studio.pipeline.mapping_audit import audit_attribute_mappings
from npv_studio.core.paths import PathGuard


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="npv-studio")
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS_PATH)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("gui", help="Launch the desktop application")
    subparsers.add_parser("check", help="Inspect dependencies without writing to the game")
    subparsers.add_parser(
        "audit-mappings",
        help="Report exact per-attribute compiler coverage and detect masked fallbacks",
    )
    sample = subparsers.add_parser("build-sample", help="Generate a safe dry-run sample build")
    sample.add_argument("--frame", choices=["female", "male"], default="female")
    inspect_package = subparsers.add_parser(
        "inspect-package", help="Read-only validation of an NPV ZIP or extracted package"
    )
    inspect_package.add_argument("path", type=Path)
    package = subparsers.add_parser(
        "package", help="Package a validated workspace staging tree for Vortex"
    )
    package.add_argument("source", type=Path)
    package.add_argument("--name", required=True)
    package.add_argument("--version", default="0.1.0-alpha")
    package.add_argument("--filename", required=True)
    analyze = subparsers.add_parser(
        "analyze-config", help="Read and normalize an abbreviated character configuration"
    )
    analyze.add_argument("path", type=Path)
    final_build = subparsers.add_parser(
        "build-npv",
        help="Generate a verified spawnable NPV and minimized Vortex ZIP",
    )
    final_build.add_argument("--config", type=Path, required=True)
    final_build.add_argument("--name")
    final_build.add_argument("--namespace")
    final_build.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly allow workspace-only WolvenKit and Blender execution",
    )
    head_test = subparsers.add_parser(
        "build-head-test", help="Run the real feminine WolvenKit/Blender head vertical slice"
    )
    head_test.add_argument("--config", type=Path, required=True)
    head_test.add_argument("--project", type=Path, required=True)
    head_test.add_argument("--name", default="Valkyrie")
    head_test.add_argument("--namespace", default="valkyrie")
    head_test.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly allow workspace-only WolvenKit and Blender execution",
    )
    hair_lineup = subparsers.add_parser(
        "build-hair-lineup",
        help="Clone a verified feminine NPV into five independently spawnable vanilla hair tests",
    )
    hair_lineup.add_argument(
        "--base-build",
        type=Path,
        required=True,
        help="Verified head-test build directory (or its source directory)",
    )
    hair_lineup.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly allow workspace-only WolvenKit execution",
    )
    npc_body = subparsers.add_parser(
        "build-npc-body-test",
        help="Build one hair-04 character using the vanilla NPC woman body",
    )
    npc_body.add_argument(
        "--base-build",
        type=Path,
        required=True,
        help="Verified head-test build directory (or its source directory)",
    )
    npc_body.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly allow workspace-only WolvenKit execution",
    )
    player_big = subparsers.add_parser(
        "build-player-big-deform-test",
        help="Build hair 04 with the vanilla player deformation controller and big body",
    )
    player_big.add_argument(
        "--base-build",
        type=Path,
        required=True,
        help="Verified head-test build directory (or its source directory)",
    )
    player_big.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly allow workspace-only WolvenKit execution",
    )
    dual_body = subparsers.add_parser(
        "build-dual-body-test",
        help="Build hair 04 with clothing-safe and nude-large AMM body toggles",
    )
    dual_body.add_argument(
        "--base-build",
        type=Path,
        required=True,
        help="Verified head-test build directory (or its source directory)",
    )
    dual_body.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly allow workspace-only WolvenKit execution",
    )
    return parser


def _sample(frame: str) -> CharacterConfig:
    if frame == "male":
        return CharacterConfig(
            name="Alpha Masculine V",
            namespace="alpha_masculine_v",
            body_frame=BodyFrame.MALE,
            voice=VoiceTone.MASCULINE,
            head=HeadShape(eyes=7, nose=1, mouth=1, jaw=1, ears=1),
        )
    return CharacterConfig(
        name="Alpha Feminine V",
        namespace="alpha_feminine_v",
        body_frame=BodyFrame.FEMALE,
        voice=VoiceTone.FEMININE,
        head=HeadShape(eyes=12, nose=1, mouth=1, jaw=1, ears=1),
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command in (None, "gui"):
        from npv_studio.app import run_gui

        return run_gui(args.settings)

    settings = load_settings(args.settings)
    guard = PathGuard(settings.game_root, settings.workspace_root)
    if args.command == "check":
        statuses = DependencyInspector(settings, guard).inspect()
        print(json.dumps([item.model_dump(mode="json") for item in statuses], indent=2))
        return 0
    if args.command == "audit-mappings":
        result = audit_attribute_mappings()
        print(json.dumps(result, indent=2))
        return 0 if result["strict_complete"] else 2
    if args.command == "build-sample":
        report = DryRunBuilder(settings).build(_sample(args.frame))
        print(json.dumps(report.as_json_data(), indent=2))
        return 0 if report.success else 2
    if args.command == "inspect-package":
        path = args.path.resolve(strict=True)
        inspector = PackageInspector()
        result = inspector.inspect_tree(path) if path.is_dir() else inspector.inspect_zip(path)
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 2
    if args.command == "package":
        filename = args.filename if args.filename.lower().endswith(".zip") else f"{args.filename}.zip"
        output = settings.workspace_root / "packages" / filename
        result = VortexPackageBuilder(guard).build(
            args.source,
            output,
            mod_name=args.name,
            version=args.version,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "analyze-config":
        result = analyze_character_source(args.path)
        print(json.dumps(result, indent=2))
        return 0 if result["safe_to_generate_supported_draft"] else 2
    if args.command == "build-npv":
        character = load_character_config(
            args.config,
            name=args.name,
            namespace=args.namespace,
        )
        result = FinalBuildBuilder(settings, execute=args.execute).build(character)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "build-head-test":
        character = character_draft_from_source(
            args.config,
            name=args.name,
            namespace=args.namespace,
        )
        result = HeadTestBuilder(settings, execute=args.execute).build(character, args.project)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "build-hair-lineup":
        result = HairLineupBuilder(settings, execute=args.execute).build(args.base_build)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "build-npc-body-test":
        result = NpcBodyTestBuilder(settings, execute=args.execute).build(args.base_build)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "build-player-big-deform-test":
        result = NpcBodyTestBuilder(
            settings,
            execute=args.execute,
            profile="player_big_deformation",
        ).build(args.base_build)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "build-dual-body-test":
        result = NpcBodyTestBuilder(
            settings,
            execute=args.execute,
            profile="dual_body",
        ).build(args.base_build)
        print(json.dumps(result, indent=2))
        return 0
    return 1
