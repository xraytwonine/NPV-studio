from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from npv_studio.core.paths import PathGuard, PathSafetyError, is_within


class PackageValidationError(RuntimeError):
    """Raised when an archive is unsafe or is not an NPV deployment tree."""


_DEPLOY_ROOTS = {"archive", "bin", "r6"}
_DRIVE_PREFIX = re.compile(r"^[a-zA-Z]:")


def _safe_parts(member_name: str) -> tuple[str, ...]:
    normalized = member_name.replace("\\", "/")
    if normalized.startswith("/") or _DRIVE_PREFIX.match(normalized):
        raise PackageValidationError(f"Archive member uses an absolute path: {member_name}")
    path = PurePosixPath(normalized)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise PackageValidationError(f"Archive member uses an unsafe path: {member_name}")
    return path.parts


def _deployment_parts(parts: tuple[str, ...], wrapper: str | None) -> tuple[str, ...]:
    return parts[1:] if wrapper else parts


def _validate_deployment_file(parts: tuple[str, ...]) -> str | None:
    path = PurePosixPath(*parts)
    suffix = path.suffix.lower()

    if parts[:3] == ("archive", "pc", "mod") and suffix in {".archive", ".xl"}:
        return "archive" if suffix == ".archive" else "archivexl"

    amm_prefix = (
        "bin",
        "x64",
        "plugins",
        "cyber_engine_tweaks",
        "mods",
        "AppearanceMenuMod",
        "Collabs",
        "Custom Entities",
    )
    if parts[: len(amm_prefix)] == amm_prefix and suffix == ".lua":
        return "amm"

    if parts[:2] == ("r6", "tweaks") and suffix in {".yaml", ".yml"}:
        return "tweakxl"

    return None


def _detect_wrapper(files: list[tuple[str, ...]]) -> str | None:
    first_parts = {parts[0] for parts in files}
    if first_parts <= _DEPLOY_ROOTS:
        return None
    if len(first_parts) == 1:
        wrapper = next(iter(first_parts))
        nested_roots = {parts[1] for parts in files if len(parts) > 1}
        if nested_roots and nested_roots <= _DEPLOY_ROOTS:
            return wrapper
    raise PackageValidationError(
        "Archive must contain archive/bin/r6 at its root, or beneath one wrapper folder"
    )


def _inspection(file_names: list[str], source: Path) -> dict[str, Any]:
    member_names = [name for name in file_names if not name.endswith(("/", "\\"))]
    safe_files = [_safe_parts(name) for name in member_names]
    if not safe_files:
        raise PackageValidationError("Package contains no files")
    wrapper = _detect_wrapper(safe_files)
    categories: dict[str, int] = {"archive": 0, "archivexl": 0, "amm": 0, "tweakxl": 0}
    invalid: list[str] = []
    deployed_names: set[str] = set()

    for original, parts in zip(member_names, safe_files, strict=True):
        deployed = _deployment_parts(parts, wrapper)
        deployed_name = PurePosixPath(*deployed).as_posix().casefold()
        if deployed_name in deployed_names:
            invalid.append(f"{original} (duplicate/case collision)")
            continue
        deployed_names.add(deployed_name)
        category = _validate_deployment_file(deployed)
        if category is None:
            invalid.append(original)
        else:
            categories[category] += 1

    errors: list[str] = []
    if invalid:
        errors.append("Unexpected deployable files: " + ", ".join(invalid))
    if categories["archive"] == 0:
        errors.append("At least one archive/pc/mod/*.archive file is required")
    if categories["amm"] == 0:
        errors.append("At least one AMM Custom Entities *.lua file is required")

    return {
        "schema_version": 1,
        "source": str(source),
        "valid": not errors,
        "wrapper_folder": wrapper,
        "file_count": len(safe_files),
        "categories": categories,
        "errors": errors,
        "warnings": (
            ["A wrapper folder is accepted; direct archive/bin/r6 roots are preferred for generation."]
            if wrapper
            else []
        ),
    }


class PackageInspector:
    """Read-only inspection for ZIPs and extracted NPV packages."""

    def inspect_zip(self, archive_path: Path) -> dict[str, Any]:
        source = Path(archive_path).resolve(strict=True)
        with ZipFile(source, "r") as archive:
            names = [info.filename for info in archive.infolist()]
            report = _inspection(names, source)
            encrypted = [info.filename for info in archive.infolist() if info.flag_bits & 0x1]
            links = [
                info.filename
                for info in archive.infolist()
                if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)
            ]
            if encrypted:
                report["errors"].append("Encrypted members are not supported")
                report["valid"] = False
            if links:
                report["errors"].append("Symbolic-link members are not supported")
                report["valid"] = False
        return report

    def inspect_tree(self, source_root: Path) -> dict[str, Any]:
        source = Path(source_root).resolve(strict=True)
        if not source.is_dir():
            raise PackageValidationError(f"Package source is not a directory: {source}")
        names: list[str] = []
        for path in sorted(source.rglob("*")):
            if path.is_dir():
                continue
            if path.is_symlink() or (
                getattr(path.lstat(), "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            ):
                raise PackageValidationError(f"Links and reparse points are forbidden: {path}")
            names.append(path.relative_to(source).as_posix())
        return _inspection(names, source)


class VortexPackageBuilder:
    """Creates a Vortex-importable ZIP without touching the game installation."""

    def __init__(self, guard: PathGuard) -> None:
        self.guard = guard
        self.inspector = PackageInspector()

    def build(
        self,
        source_root: Path,
        output_zip: Path,
        *,
        mod_name: str,
        version: str,
        export_root: Path | None = None,
    ) -> dict[str, Any]:
        source = Path(source_root).resolve(strict=True)
        if not is_within(source, self.guard.workspace_root):
            raise PathSafetyError(f"Package source must be inside workspace: {source}")
        target = (
            self.guard.assert_export_path(output_zip, export_root)
            if export_root is not None
            else self.guard.assert_write_path(output_zip)
        )
        if target.suffix.lower() != ".zip":
            raise PackageValidationError("Vortex package output must use the .zip extension")
        if not mod_name.strip() or not version.strip():
            raise PackageValidationError("Mod name and version must not be empty")

        inspection = self.inspector.inspect_tree(source)
        if not inspection["valid"]:
            raise PackageValidationError("; ".join(inspection["errors"]))
        if inspection["wrapper_folder"] is not None:
            raise PackageValidationError("Generated package staging must use direct archive/bin/r6 roots")

        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(source.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(source).as_posix()
                info = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = (0o100644 & 0xFFFF) << 16
                with path.open("rb") as source_file, archive.open(info, "w") as member:
                    shutil.copyfileobj(source_file, member, length=1024 * 1024)

        hasher = hashlib.sha256()
        with target.open("rb") as package_file:
            for block in iter(lambda: package_file.read(1024 * 1024), b""):
                hasher.update(block)
        digest = hasher.hexdigest()
        manifest = {
            "schema_version": 1,
            "package_type": "vortex_importable_zip",
            "game": "Cyberpunk 2077",
            "nexus_game_domain": "cyberpunk2077",
            "steam_app_id": 1091500,
            "mod_name": mod_name.strip(),
            "version": version.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "archive": str(target),
            "sha256": digest,
            "installation_owner": "Vortex",
            "direct_game_writes": False,
            "inspection": self.inspector.inspect_zip(target),
        }
        manifest_path = target.with_suffix(".manifest.json")
        if export_root is not None:
            safe_manifest = self.guard.assert_export_path(manifest_path, export_root)
            safe_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        else:
            self.guard.write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
        return manifest
