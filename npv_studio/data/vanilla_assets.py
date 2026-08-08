from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def load_hair_styles() -> dict[str, dict[int, dict[str, Any]]]:
    resource = files("npv_studio.data").joinpath("vanilla_assets/hair_styles.json")
    document = json.loads(resource.read_text(encoding="utf-8"))
    result: dict[str, dict[int, dict[str, Any]]] = {}
    for frame in ("female", "male"):
        result[frame] = {}
        for raw_selection, raw_definition in document[frame].items():
            selection = int(raw_selection)
            definition = dict(raw_definition)
            # Native Hair 50 deliberately reuses Hair 14's buzz-cap geometry,
            # but its mesh appearances are the distinct ``*_afro`` variants.
            # This suffix is part of the asset identity, not a display label.
            definition["color_suffix"] = "_afro" if selection == 50 else ""
            definition["meshes"] = tuple(
                ("hh_hair" if index == 0 else f"hh_hair_part_{index + 1:02d}", path)
                for index, path in enumerate(definition["meshes"])
            )
            controller = definition.get("controller")
            if controller is not None:
                definition["controller"] = {
                    "name": "hair_dangle",
                    "rig": controller["rig"],
                    "graph": controller["graph"],
                }
            result[frame][selection] = definition
    return result
