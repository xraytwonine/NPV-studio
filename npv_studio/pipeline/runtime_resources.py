from __future__ import annotations

from pathlib import Path
from typing import Iterable

from npv_studio.core.paths import PathGuard


def _tree_stats(root: Path) -> tuple[int, int]:
    files = [path for path in root.rglob("*") if path.is_file()]
    return len(files), sum(path.stat().st_size for path in files)


def prune_runtime_resources(
    guard: PathGuard,
    archive_root: Path,
    selected_head_mesh_stems: Iterable[str],
    *,
    character_directory: str,
) -> dict[str, object]:
    """Remove template build inputs from a copied runtime archive.

    Prepared morph targets are consumed by Blender and WolvenKit before this
    function is called. The imported REDengine ``.mesh`` files contain the
    baked result, so the morph targets must not be shipped in the Vortex mod.
    Unselected template head variants are likewise unused by the compiled app.

    Body meshes and textures are deliberately left alone. Some template body
    components are stored as hashed depot paths in the app resource, and a
    conservative runtime package is preferable to an incomplete one.
    """

    safe_archive_root = guard.assert_write_path(archive_root)
    character_root = safe_archive_root / "tutorial" / "npv" / character_directory
    head_root = character_root / "head"
    if not head_root.is_dir():
        raise FileNotFoundError(f"Template head resource directory is missing: {head_root}")

    keep_names = {f"{stem}.mesh" for stem in selected_head_mesh_stems}
    missing = sorted(name for name in keep_names if not (head_root / name).is_file())
    if missing:
        raise FileNotFoundError(
            "Selected runtime head meshes are missing: " + ", ".join(missing)
        )

    before_count, before_bytes = _tree_stats(safe_archive_root)
    removed: list[dict[str, object]] = []

    morph_root = head_root / "morphtargets"
    if morph_root.is_dir():
        for path in sorted(
            morph_root.rglob("*"), key=lambda item: len(item.parts), reverse=True
        ):
            if path.is_file():
                size = path.stat().st_size
                removed.append(
                    {
                        "path": str(path.relative_to(safe_archive_root)),
                        "category": "build_input_morphtarget",
                        "bytes": size,
                    }
                )
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        morph_root.rmdir()

    for path in sorted(head_root.glob("*.mesh")):
        if path.name not in keep_names:
            size = path.stat().st_size
            removed.append(
                {
                    "path": str(path.relative_to(safe_archive_root)),
                    "category": "unselected_head_variant",
                    "bytes": size,
                }
            )
            path.unlink()

    after_count, after_bytes = _tree_stats(safe_archive_root)
    removed_by_category: dict[str, dict[str, int]] = {}
    for item in removed:
        category = str(item["category"])
        summary = removed_by_category.setdefault(category, {"files": 0, "bytes": 0})
        summary["files"] += 1
        summary["bytes"] += int(item["bytes"])

    return {
        "before": {"files": before_count, "bytes": before_bytes},
        "after": {"files": after_count, "bytes": after_bytes},
        "removed": {
            "files": before_count - after_count,
            "bytes": before_bytes - after_bytes,
            "by_category": removed_by_category,
        },
        "kept_head_meshes": sorted(keep_names),
        "removed_files": removed,
    }


def prune_female_runtime_resources(
    guard: PathGuard,
    archive_root: Path,
    selected_head_mesh_stems: Iterable[str],
) -> dict[str, object]:
    return prune_runtime_resources(
        guard,
        archive_root,
        selected_head_mesh_stems,
        character_directory="your_female_character",
    )


def prune_male_runtime_resources(
    guard: PathGuard,
    archive_root: Path,
    selected_head_mesh_stems: Iterable[str],
) -> dict[str, object]:
    return prune_runtime_resources(
        guard,
        archive_root,
        selected_head_mesh_stems,
        character_directory="your_male_character",
    )
