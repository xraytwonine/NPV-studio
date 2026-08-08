from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from npv_studio.adapters.process import ExternalToolRunner, ProcessResult
from npv_studio.core.paths import PathGuard
from npv_studio.core.runtime import bundled_resource_root
from npv_studio.domain.models import AppSettings, BodyFrame, CharacterConfig
from npv_studio.pipeline.creator_assets import frame_code


BLENDER_BODY_WORKER = bundled_resource_root() / "blender" / "generate_body_asset.py"
BODY_SCAR_CHUNK_MASKS = {
    1: 18446744073709551601,
    2: 18446744073709551602,
    3: 18446744073709551604,
    4: 18446744073709551608,
}
PUBIC_HAIR_STYLES = {
    1: "bush",
    2: "chaplin",
    3: "heart",
    4: "landing_strip",
    5: "lighting_bolt",
}
PUBIC_HAIR_COLORS = {1: "black", 2: "blonde", 3: "ginger", 4: "green", 5: "pink"}


def body_scar_depot_path(frame: BodyFrame, chest: str) -> str:
    code = frame_code(frame)
    if frame is BodyFrame.MALE:
        return (
            "base\\characters\\common\\player_base_bodies\\player_man_average\\scars\\"
            "t0_000_pma_base__scars.mesh"
        )
    return (
        "tutorial\\npv\\your_female_character\\body\\"
        f"t0_000_{code}_base__scars_{chest}.mesh"
    )


def female_nipple_depot_path(chest: str) -> str:
    return (
        "tutorial\\npv\\your_female_character\\body\\"
        f"i0_000_pwa_base__nipple_{chest}.mesh"
    )


def genital_depot_path(frame: BodyFrame, genitals: str, penis_size: str) -> str | None:
    code = frame_code(frame)
    frame_root = "player_female_average" if frame is BodyFrame.FEMALE else "player_man_average"
    if genitals == "none":
        if frame is BodyFrame.MALE:
            return None
        return (
            "base\\characters\\common\\player_base_bodies\\player_female_average\\genitals\\"
            "i0_000_pwa_base__genitals_none.mesh"
        )
    if genitals == "vagina":
        return (
            f"base\\characters\\common\\player_base_bodies\\{frame_root}\\genitals\\"
            f"i0_000_{code}_base__vagina.mesh"
        )
    suffix = "penis" if genitals == "penis_1" else "penis_circumcised"
    return (
        f"tutorial\\npv\\your_{frame.value}_character\\body\\"
        f"i0_000_{code}_base__{suffix}_{penis_size}.mesh"
    )


def pubic_hair_depot_path(
    frame: BodyFrame, genitals: str, penis_size: str
) -> str | None:
    if genitals == "none":
        return None
    code = frame_code(frame)
    frame_root = "player_female_average" if frame is BodyFrame.FEMALE else "player_man_average"
    if genitals == "vagina":
        return (
            f"base\\characters\\common\\player_base_bodies\\{frame_root}\\genitals\\"
            f"i0_000_{code}_base__vagina_hairstyle_01.mesh"
        )
    suffix = "penis" if genitals == "penis_1" else "penis_circumcised"
    return (
        f"tutorial\\npv\\your_{frame.value}_character\\body\\"
        f"i0_000_{code}_base__{suffix}_hairstyle_01_{penis_size}.mesh"
    )


def pubic_hair_appearance(style: int, color: int) -> str:
    return f"{PUBIC_HAIR_STYLES[style]}_{PUBIC_HAIR_COLORS[color]}"


@dataclass(frozen=True)
class _BakeAsset:
    source_depot: str
    placeholder: Path | None
    placeholder_depot: str | None
    output_mesh: Path
    output_stem: str
    shape: str | None


class BodyAssetBuildError(RuntimeError):
    pass


def _require_success(stage: str, result: ProcessResult) -> None:
    if result.returncode != 0:
        raise BodyAssetBuildError(
            f"{stage} failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class BodyAssetBuilder:
    """Bake selected body morphtargets entirely inside a build workspace."""

    def __init__(self, settings: AppSettings, *, execute: bool = False) -> None:
        self.settings = settings
        self.guard = PathGuard(settings.game_root, settings.workspace_root)
        self.runner = ExternalToolRunner(self.guard, enabled=execute)

    def _template_placeholder(self, name: str) -> Path:
        root = self.settings.npv_template_root
        if root is None:
            raise BodyAssetBuildError("No NPV template is configured")
        path = (
            Path(root)
            / "source"
            / "archive"
            / "tutorial"
            / "npv"
            / "your_male_character"
            / "body"
            / name
        )
        if not path.is_file():
            raise BodyAssetBuildError(f"Required body placeholder is missing: {path}")
        return path

    def _assets(self, source_root: Path, character: CharacterConfig) -> list[_BakeAsset]:
        selection = character.appearance
        frame = character.body_frame
        code = frame_code(frame)
        body_root = source_root / "archive" / "tutorial" / "npv" / f"your_{frame.value}_character" / "body"
        assets: list[_BakeAsset] = []
        if frame is BodyFrame.FEMALE and selection.body_scars:
            for chest in dict.fromkeys((selection.chest, "default", "big")):
                assets.append(_BakeAsset(
                    source_depot=(
                        "base\\characters\\common\\player_base_bodies\\player_female_average\\scars\\"
                        "t0_000_pwa_base__scars.morphtarget"
                    ),
                    placeholder=None,
                    placeholder_depot=(
                        "base\\characters\\common\\player_base_bodies\\player_man_average\\scars\\"
                        "t0_000_pma_base__scars.mesh"
                    ),
                    output_mesh=body_root / f"t0_000_pwa_base__scars_{chest}.mesh",
                    output_stem=f"t0_000_pwa_base__scars_{chest}",
                    shape=(None if chest == "default" else f"breast_{chest}"),
                ))
        if frame is BodyFrame.FEMALE and selection.nipples:
            for chest in dict.fromkeys((selection.chest, "default", "big")):
                assets.append(
                    _BakeAsset(
                        source_depot=(
                            "base\\characters\\common\\player_base_bodies\\"
                            "player_female_average\\genitals\\"
                            "i0_000_pwa_base__nipple.morphtarget"
                        ),
                        placeholder=None,
                        placeholder_depot=(
                            "base\\characters\\common\\player_base_bodies\\"
                            "player_female_average\\genitals\\"
                            "i0_000_pwa_base__nipple.mesh"
                        ),
                        output_mesh=(
                            body_root / f"i0_000_pwa_base__nipple_{chest}.mesh"
                        ),
                        output_stem=f"i0_000_pwa_base__nipple_{chest}",
                        shape=(None if chest == "default" else f"breast_{chest}"),
                    )
                )
        if selection.genitals.startswith("penis"):
            suffix = "penis" if selection.genitals == "penis_1" else "penis_circumcised"
            size = selection.penis_size
            shape = None if size == "default" else f"penis_{size}"
            frame_root = "player_female_average" if frame is BodyFrame.FEMALE else "player_man_average"
            assets.append(
                _BakeAsset(
                    source_depot=(
                        f"base\\characters\\common\\player_base_bodies\\{frame_root}\\genitals\\"
                        f"i0_000_{code}_base__{suffix}.morphtarget"
                    ),
                    placeholder=self._template_placeholder("i0_000_pma_base__penis.mesh"),
                    placeholder_depot=None,
                    output_mesh=body_root / f"i0_000_{code}_base__{suffix}_{size}.mesh",
                    output_stem=f"i0_000_{code}_base__{suffix}_{size}",
                    shape=shape,
                )
            )
            if selection.pubic_hair_style:
                assets.append(
                    _BakeAsset(
                        source_depot=(
                            f"base\\characters\\common\\player_base_bodies\\{frame_root}\\genitals\\"
                            f"i0_000_{code}_base__{suffix}_hairstyle_01.morphtarget"
                        ),
                        placeholder=self._template_placeholder("i0_000_pma_base__penis_hairstyle_01.mesh"),
                        placeholder_depot=None,
                        output_mesh=(
                            body_root / f"i0_000_{code}_base__{suffix}_hairstyle_01_{size}.mesh"
                        ),
                        output_stem=f"i0_000_{code}_base__{suffix}_hairstyle_01_{size}",
                        shape=shape,
                    )
                )
        return assets

    def build(self, build_root: Path, source_root: Path, character: CharacterConfig) -> dict[str, Any]:
        build = self.guard.assert_write_path(build_root)
        source = self.guard.assert_write_path(source_root)
        assets = self._assets(source, character)
        if not assets:
            return {"status": "not_required", "assets": [], "processes": []}
        if self.settings.wolvenkit_executable is None or not self.settings.wolvenkit_executable.is_file():
            raise BodyAssetBuildError("A valid WolvenKit CLI executable is required")
        if self.settings.blender_executable is None or not self.settings.blender_executable.is_file():
            raise BodyAssetBuildError("A valid Blender executable is required")
        if not BLENDER_BODY_WORKER.is_file():
            raise BodyAssetBuildError(f"Bundled Blender body worker is missing: {BLENDER_BODY_WORKER}")

        work = self.guard.ensure_directory(build / "body_asset_bake")
        cooked = self.guard.ensure_directory(work / "cooked")
        raw = self.guard.ensure_directory(work / "raw")
        glb_out = self.guard.ensure_directory(work / "baked")
        processes: list[dict[str, Any]] = []
        archive_source = self.guard.assert_game_read_path(
            self.settings.game_root / "archive" / "pc" / "content"
        )
        request_assets: list[dict[str, Any]] = []
        resolved_placeholders: dict[Path, Path] = {}
        for asset in assets:
            extract = self.runner.run(
                self.settings.wolvenkit_executable,
                [
                    "extract", str(archive_source), "--outpath", str(cooked),
                    "--pattern", asset.source_depot, "--gamepath", str(self.settings.game_root),
                    "--verbosity", "Minimal",
                ],
                build,
            )
            _require_success(f"Extract {asset.source_depot}", extract)
            processes.append({"stage": "extract", "command": list(extract.command), "stdout": extract.stdout})
            cooked_source = cooked / Path(*asset.source_depot.split("\\"))
            if not cooked_source.is_file():
                raise BodyAssetBuildError(f"WolvenKit did not extract {asset.source_depot}")
            if asset.placeholder_depot:
                extract_placeholder = self.runner.run(
                    self.settings.wolvenkit_executable,
                    [
                        "extract", str(archive_source), "--outpath", str(cooked),
                        "--pattern", asset.placeholder_depot,
                        "--gamepath", str(self.settings.game_root), "--verbosity", "Minimal",
                    ],
                    build,
                )
                _require_success(f"Extract {asset.placeholder_depot}", extract_placeholder)
                placeholder = cooked / Path(*asset.placeholder_depot.split("\\"))
                if not placeholder.is_file():
                    raise BodyAssetBuildError(
                        f"WolvenKit did not extract placeholder {asset.placeholder_depot}"
                    )
                resolved_placeholders[asset.output_mesh] = placeholder
            elif asset.placeholder is not None:
                resolved_placeholders[asset.output_mesh] = asset.placeholder
            else:
                raise BodyAssetBuildError(f"No placeholder configured for {asset.output_mesh.name}")
            export = self.runner.run(
                self.settings.wolvenkit_executable,
                [
                    "export", str(cooked_source), "--outpath", str(raw),
                    "--gamepath", str(self.settings.game_root), "--verbosity", "Minimal",
                ],
                build,
            )
            _require_success(f"Export {asset.source_depot}", export)
            processes.append({"stage": "export", "command": list(export.command), "stdout": export.stdout})
            source_glb = raw / f"{cooked_source.name}.glb"
            if not source_glb.is_file():
                raise BodyAssetBuildError(f"WolvenKit did not export {source_glb.name}")
            request_assets.append(
                {
                    "source_glb": str(source_glb),
                    "output_glb": str(glb_out / f"{asset.output_stem}.glb"),
                    "stem": asset.output_stem,
                    "shape": asset.shape,
                }
            )

        request_path = self.guard.write_text(
            work / "body-assets-request.json",
            json.dumps({"schema_version": 1, "assets": request_assets}, indent=2) + "\n",
        )
        blender = self.runner.run(
            self.settings.blender_executable,
            ["--background", "--python", str(BLENDER_BODY_WORKER), "--", str(request_path)],
            build,
        )
        _require_success("Blender body-asset bake", blender)
        processes.append({"stage": "blender", "command": list(blender.command), "stdout": blender.stdout})
        result_path = work / "body-assets-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not result.get("success"):
            raise BodyAssetBuildError(f"Blender body bake failed: {result.get('error')}")

        emitted: list[dict[str, Any]] = []
        for asset in assets:
            asset.output_mesh.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resolved_placeholders[asset.output_mesh], asset.output_mesh)
            before = _sha256(asset.output_mesh)
            glb = glb_out / f"{asset.output_stem}.glb"
            imported = self.runner.run(
                self.settings.wolvenkit_executable,
                ["import", str(glb), "--outpath", str(asset.output_mesh.parent), "--keep", "--verbosity", "Minimal"],
                build,
            )
            _require_success(f"Import {glb.name}", imported)
            processes.append({"stage": "import", "command": list(imported.command), "stdout": imported.stdout})
            if not asset.output_mesh.is_file() or _sha256(asset.output_mesh) == before:
                raise BodyAssetBuildError(f"WolvenKit did not rebuild {asset.output_mesh.name}")
            emitted.append(
                {
                    "source_depot": asset.source_depot,
                    "output_mesh": str(asset.output_mesh),
                    "shape": asset.shape,
                    "sha256": _sha256(asset.output_mesh),
                }
            )
        return {"status": "complete", "assets": emitted, "processes": processes}
