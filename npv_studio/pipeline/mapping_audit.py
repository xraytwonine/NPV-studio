from __future__ import annotations

from collections import defaultdict
from typing import Any, Hashable

from npv_studio.domain.models import BodyFrame
from npv_studio.pipeline.appearance import (
    BODY_TATTOO_APPEARANCE_SUFFIX,
    CHEEK_MAKEUP_COLORS,
    EYE_COLORS,
    EYE_MAKEUP_COLORS,
    EYELASH_COLORS,
    FEMALE_BODY_MESHES,
    FEMALE_BIG_NIPPLES,
    FEMALE_NIPPLE_APPEARANCE_SUFFIX,
    FEMALE_BODY_TATTOOS,
    FEMALE_HAIR_STYLES,
    FRECKLE_MAKEUP_COLORS,
    HAIR_COLORS,
    LIP_MAKEUP_COLORS,
    MALE_BLEMISH_COLORS,
    MALE_BODY_TATTOOS,
    MALE_HAIR_STYLES,
    NAIL_COLORS,
    NAIL_MESHES,
    SKIN_TONES,
    TEETH_APPEARANCES,
)
from npv_studio.pipeline.creator_assets import (
    BEARD_MESHES,
    BEARD_SHADOW_APPEARANCES,
    BEARD_STYLE_CHUNK_MASKS,
    CYBERWARE,
    FACIAL_SCAR_CHUNK_MASKS,
    FACIAL_TATTOO_APPEARANCE_SUFFIXES,
    FACIAL_TATTOO_CHUNK_MASKS,
    FACIAL_TATTOO_MESHES,
    PIERCING_COLORS,
    PIERCINGS,
)
from npv_studio.pipeline.body_assets import (
    BODY_SCAR_CHUNK_MASKS,
    PUBIC_HAIR_COLORS,
    PUBIC_HAIR_STYLES,
    body_scar_depot_path,
    genital_depot_path,
    pubic_hair_appearance,
    pubic_hair_depot_path,
)


# This is a compiler-coverage ledger, never a UI-range ledger.  A field is
# complete only when every selectable value has a correct compiler outcome for
# every applicable frame.  Merely accepting an integer is not evidence.
COMPILER_COVERAGE: dict[str, tuple[str, str]] = {
    "head.eyes": ("complete", "Baked into every selected head component by Blender morph channel 1."),
    "head.nose": ("complete", "Baked into every selected head component by Blender morph channel 2."),
    "head.mouth": ("complete", "Baked into every selected head component by Blender morph channel 3."),
    "head.jaw": ("complete", "Baked into every selected head component by Blender morph channel 4."),
    "head.ears": ("complete", "Baked into every selected head component by Blender morph channel 5."),
    "appearance.skin_tone": ("complete", "12 distinct vanilla head/body appearance identities."),
    "appearance.skin_type": ("complete", "5 distinct complexion suffixes."),
    "appearance.hairstyle": ("complete", "50 exact frame-specific mesh/shadow/controller signatures."),
    "appearance.hair_color": ("complete", "35 distinct vanilla material appearances."),
    "appearance.eye_color": ("complete", "39 distinct vanilla eye appearances."),
    "appearance.teeth": ("complete", "Five distinct vanilla teeth appearances."),
    "appearance.nail_style": ("complete", "Short/long frame-specific left/right meshes."),
    "appearance.nail_color": ("complete", "37 distinct vanilla nail appearances."),
    "appearance.cyberware": ("complete", "Eight exact source-mesh, frame-material and chunk signatures."),
    "appearance.facial_scars": ("complete", "Nine exact scar chunk masks on the baked scar mesh."),
    "appearance.facial_tattoos": ("complete", "Eleven exact mesh/material/chunk signatures; choices 5/6 share geometry but not output identity."),
    "appearance.piercings": ("complete", "All frame-valid multi-mesh sets and chunk masks are compiled."),
    "appearance.piercing_color": ("complete", "Sixteen distinct piercing materials are applied."),
    "appearance.eye_makeup": ("complete", "Selected style is encoded in the baked eye-makeup material appearance."),
    "appearance.eye_makeup_color": ("complete", "Fourteen exact eye-makeup material families."),
    "appearance.lip_makeup": ("complete", "Selected style is encoded in the baked lipstick material appearance."),
    "appearance.lip_makeup_color": ("complete", "Fourteen exact lipstick material families."),
    "appearance.lip_makeup_finish": ("complete", "Default, glossy and matte material suffixes are distinct."),
    "appearance.cheek_makeup": ("complete", "Selected style is encoded in the baked cheek material appearance."),
    "appearance.cheek_makeup_color": ("complete", "Eight exact cheek material families."),
    "appearance.blemishes": ("complete", "Three exact blemish chunk outcomes are compiled."),
    "appearance.blemish_color": ("complete", "Six exact blemish material appearances."),
    "appearance.eyebrows": ("complete", "Off and all 11 shapes compile to the frame-specific baked eyebrow component."),
    "appearance.eyebrow_color": ("complete", "All 35 exact hair-material families are applied to eyebrows on both frames."),
    "appearance.eyelash_color": ("complete", "All 35 colors compile to an eyelash-only chunk of the baked eye mesh."),
    "appearance.beard": ("complete", "All 12 masculine shapes compile to their exact baked mesh and shadow signatures."),
    "appearance.beard_style": ("complete", "Every shape-valid style compiles to its exact vanilla CR2W chunk mask."),
    "appearance.beard_color": ("complete", "All 35 colors compile on colorable beard geometry; stubble is primary-gated."),
    "appearance.body_tattoos": ("complete", "All seven creator choices compile to exact frame mesh and material identities; choices 6/7 intentionally reuse geometry with distinct materials."),
    "appearance.body_scars": ("complete", "All four exact scar chunks compile; feminine chest morphs are baked to distinct meshes."),
    "appearance.nipples": ("complete", "All three feminine choices compile to chest-matched nipple geometry with distinct material identities; masculine selection is frame-gated."),
    "appearance.chest": ("complete", "Default, small and big each select an exact primary torso and chest-matched overlays."),
    "appearance.genitals": ("complete", "None and vagina compile normally; uncircumcised and circumcised selections compile to frame-specific geometry that is disabled on spawn for manual AMM activation."),
    "appearance.penis_size": ("complete", "Small, default and big penis morphs are baked to distinct frame-specific meshes and emitted disabled on spawn."),
    "appearance.pubic_hair_style": ("complete", "All five exact vanilla geometry appearances compile on vagina and penis bases; penile pubic hair follows the disabled penis state."),
    "appearance.pubic_hair_color": ("complete", "All five exact vanilla pubic-hair material families compile."),
}


def _hair_identity(definition: dict[str, Any]) -> tuple[Hashable, ...]:
    controller = definition["controller"]
    return (
        tuple(definition["meshes"]),
        definition["shadow"],
        None if controller is None else (controller["rig"], controller["graph"]),
        definition["color_suffix"],
    )


def _aliases(catalog: dict[int, Hashable]) -> list[list[int]]:
    by_identity: dict[Hashable, list[int]] = defaultdict(list)
    for selection, identity in catalog.items():
        by_identity[identity].append(selection)
    return [values for values in by_identity.values() if len(values) > 1]


def _identity_catalogs() -> dict[str, dict[int, Hashable]]:
    catalogs: dict[str, dict[int, Hashable]] = {
        "skin_tone": dict(SKIN_TONES),
        "hair_color": dict(HAIR_COLORS),
        "eyebrow_shape": {
            selection: ("off" if selection == 0 else f"shape_{selection:02d}")
            for selection in range(0, 12)
        },
        "eye_color": dict(EYE_COLORS),
        "eyelash_color": dict(EYELASH_COLORS),
        "male_beard_shape": {
            shape: (tuple(BEARD_MESHES[shape]), BEARD_SHADOW_APPEARANCES[shape])
            for shape in BEARD_MESHES
        },
        "male_beard_shape_style": {
            shape * 10 + style: (
                BEARD_MESHES[shape][-1],
                BEARD_STYLE_CHUNK_MASKS[shape][style],
            )
            for shape in BEARD_MESHES
            for style in BEARD_STYLE_CHUNK_MASKS[shape]
        },
        "male_beard_color": dict(HAIR_COLORS),
        "teeth": dict(TEETH_APPEARANCES),
        "nail_color": dict(NAIL_COLORS),
        "eye_makeup_color": dict(EYE_MAKEUP_COLORS),
        "cheek_makeup_color": dict(CHEEK_MAKEUP_COLORS),
        "freckle_makeup_combinations": {
            (color - 1) * 4 + style: appearance
            for color, appearances in FRECKLE_MAKEUP_COLORS.items()
            for style, appearance in enumerate(appearances, 1)
        },
        "lip_makeup_color": dict(LIP_MAKEUP_COLORS),
        "blemish_color": dict(MALE_BLEMISH_COLORS),
        "piercing_color": dict(PIERCING_COLORS),
        "female_hairstyle": {
            selection: _hair_identity(definition)
            for selection, definition in FEMALE_HAIR_STYLES.items()
        },
        "male_hairstyle": {
            selection: _hair_identity(definition)
            for selection, definition in MALE_HAIR_STYLES.items()
        },
        "facial_scars": {
            selection: ("scars_01", chunk)
            for selection, chunk in FACIAL_SCAR_CHUNK_MASKS.items()
        },
        "facial_tattoos": {
            selection: (
                FACIAL_TATTOO_MESHES[selection],
                FACIAL_TATTOO_CHUNK_MASKS[selection],
                FACIAL_TATTOO_APPEARANCE_SUFFIXES[selection],
            )
            for selection in FACIAL_TATTOO_MESHES
        },
        "female_piercings": {
            selection: tuple(parts) for selection, parts in PIERCINGS[BodyFrame.FEMALE].items()
        },
        "male_piercings": {
            selection: tuple(parts) for selection, parts in PIERCINGS[BodyFrame.MALE].items()
        },
        "female_nail_style": {
            index: tuple(sorted(meshes.items()))
            for index, meshes in enumerate(NAIL_MESHES[BodyFrame.FEMALE].values(), 1)
        },
        "male_nail_style": {
            index: tuple(sorted(meshes.items()))
            for index, meshes in enumerate(NAIL_MESHES[BodyFrame.MALE].values(), 1)
        },
        "female_body_tattoo_default": {
            selection: (mesh, BODY_TATTOO_APPEARANCE_SUFFIX[selection])
            for selection, mesh in FEMALE_BODY_TATTOOS["default"].items()
        },
        "female_body_tattoo_big": {
            selection: (mesh, BODY_TATTOO_APPEARANCE_SUFFIX[selection])
            for selection, mesh in FEMALE_BODY_TATTOOS["big"].items()
        },
        "male_body_tattoo": {
            selection: (mesh, BODY_TATTOO_APPEARANCE_SUFFIX[selection])
            for selection, mesh in MALE_BODY_TATTOOS.items()
        },
        "female_nipples": {
            selection: (mesh, FEMALE_NIPPLE_APPEARANCE_SUFFIX[selection])
            for selection, mesh in FEMALE_BIG_NIPPLES.items()
        },
        "female_chest": dict(FEMALE_BODY_MESHES),
        "body_scars": dict(BODY_SCAR_CHUNK_MASKS),
        "female_genitals": {
            0: "female_none",
            1: genital_depot_path(BodyFrame.FEMALE, "vagina", "unavailable"),
            2: genital_depot_path(BodyFrame.FEMALE, "penis_1", "default"),
            3: genital_depot_path(BodyFrame.FEMALE, "penis_2", "default"),
        },
        "male_genitals": {
            0: "male_none",
            1: genital_depot_path(BodyFrame.MALE, "vagina", "unavailable"),
            2: genital_depot_path(BodyFrame.MALE, "penis_1", "default"),
            3: genital_depot_path(BodyFrame.MALE, "penis_2", "default"),
        },
        "female_penis_size": {
            index: genital_depot_path(BodyFrame.FEMALE, "penis_1", size)
            for index, size in enumerate(("small", "default", "big"), 1)
        },
        "male_penis_size": {
            index: genital_depot_path(BodyFrame.MALE, "penis_1", size)
            for index, size in enumerate(("small", "default", "big"), 1)
        },
        "pubic_hair_style": dict(PUBIC_HAIR_STYLES),
        "pubic_hair_color": dict(PUBIC_HAIR_COLORS),
        "female_pubic_combinations": {
            (style - 1) * 5 + color: (
                pubic_hair_depot_path(BodyFrame.FEMALE, "vagina", "unavailable"),
                pubic_hair_appearance(style, color),
            )
            for style in PUBIC_HAIR_STYLES
            for color in PUBIC_HAIR_COLORS
        },
    }
    for frame in BodyFrame:
        catalogs[f"{frame.value}_cyberware"] = {
            selection: (definition["mesh"], definition[frame.value], definition["chunk_mask"])
            for selection, definition in CYBERWARE.items()
        }
    return catalogs


def audit_attribute_mappings() -> dict[str, Any]:
    catalogs = _identity_catalogs()
    collisions = {
        name: duplicate_sets
        for name, catalog in catalogs.items()
        if (duplicate_sets := _aliases(catalog))
    }
    rows = [
        {"field": field, "status": status, "evidence": evidence}
        for field, (status, evidence) in COMPILER_COVERAGE.items()
    ]
    complete = [row["field"] for row in rows if row["status"] == "complete"]
    incomplete = [row["field"] for row in rows if row["status"] != "complete"]
    strict_complete = not incomplete and not collisions
    return {
        "schema_version": 2,
        "strict_complete": strict_complete,
        "complete_field_count": len(complete),
        "incomplete_field_count": len(incomplete),
        "identity_catalog_counts": {name: len(catalog) for name, catalog in catalogs.items()},
        "identity_collisions": collisions,
        "fields": rows,
        "release_gate": (
            "pass"
            if strict_complete
            else "blocked: visible controls still lack exact compiler outcomes or contain aliases"
        ),
    }
