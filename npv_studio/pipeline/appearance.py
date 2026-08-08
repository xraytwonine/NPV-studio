from __future__ import annotations

from copy import deepcopy
from typing import Any

from npv_studio.data.loader import load_game_data
from npv_studio.data.vanilla_assets import load_hair_styles
from npv_studio.domain.models import BodyFrame, BuildMode, CharacterConfig
from npv_studio.pipeline.creator_assets import (
    BEARD_MESHES,
    BEARD_SHADOW_APPEARANCES,
    BEARD_STYLE_CHUNK_MASKS,
    CYBERWARE,
    FACIAL_TATTOO_APPEARANCE_SUFFIXES,
    FACIAL_TATTOO_CHUNK_MASKS,
    FACIAL_SCAR_CHUNK_MASKS,
    FACIAL_TATTOO_MESHES,
    PIERCING_COLORS,
    PIERCINGS,
    frame_code,
)
from npv_studio.pipeline.body_assets import (
    BODY_SCAR_CHUNK_MASKS,
    body_scar_depot_path,
    female_nipple_depot_path,
    genital_depot_path,
    pubic_hair_appearance,
    pubic_hair_depot_path,
)


GENERATED_HEAD_COMPONENT_NAMES = {
    "h0_cyberware_face",
    "hx_facial_scars",
    "h0_tattoo",
    "hx_makeup_eyes",
    "hx_cheek_makeup",
    "hx_blemishes",
    "hx_makeup_freckles",
    "hx_makeup_lips_01",
    "i1_earring",
    "hel_eyelashes",
    "hb_beard_shadow",
    "hb_beard",
}


def _is_generated_head_component(name: str | None) -> bool:
    return bool(
        name in GENERATED_HEAD_COMPONENT_NAMES
        or (name and name.startswith("i1_earring_"))
    )


SKIN_TONES = {
    1: "01_ca_pale",
    2: "01_ca_pale_00_warm_ivory",
    3: "02_ca_limestone",
    4: "02_ca_limestone_00_beige",
    5: "03_ca_senna",
    6: "03_ca_senna_00_amber",
    7: "03_ca_senna_01_honey",
    8: "03_ca_senna_02_band",
    9: "04_ca_almond",
    10: "04_ca_almond_00_umber",
    11: "05_bl_espresso",
    12: "06_bl_dark",
}

HAIR_COLORS = {
    1: "brown_liquorice",
    2: "blonde_platinum",
    3: "red_merlot",
    4: "ginger_copper",
    5: "teal_ombre",
    6: "black_carbon",
    7: "blonde_golden",
    8: "blonde_dishwater",
    9: "blue_sapphire",
    10: "brown_ombre",
    11: "red_apple",
    12: "gray_gunmetal",
    13: "ginger_strawberry",
    14: "teal_ash",
    15: "pink_magenta",
    16: "pink_rose",
    17: "blue_steel",
    18: "blue_red_ombre",
    19: "cold_white",
    20: "cyberpunk_yellow",
    21: "goblin_green",
    22: "liliac",
    23: "mermaid_aquamarine",
    24: "purple_ombre",
    25: "black_salt_n_pepper",
    26: "green_toxic",
    27: "brown_medium",
    28: "blue_sky",
    29: "citrus_yellow",
    30: "dark_purple",
    31: "green_orange",
    32: "liliac_ombre",
    33: "phoenix_fire",
    34: "purple_blonde",
    35: "silver_rose",
}

EYE_COLORS = {
    1: "gradient_brown",
    2: "gradient_blue",
    3: "gradient_black",
    4: "gradient_green",
    5: "gradient_grey",
    6: "gradient_light_blue",
    7: "gradient_red",
    8: "gradient_violet",
    9: "gradient_yellow",
    10: "blood_gradient_black",
    11: "blood_gradient_blue",
    12: "blood_gradient_brown",
    13: "blood_gradient_green",
    14: "blood_gradient_grey",
    15: "blood_gradient_light_blue",
    16: "blood_gradient_red",
    17: "blood_gradient_violet",
    18: "blood_gradient_yellow",
    19: "multilayer_arasaka",
    20: "multilayer_arasaka_black",
    21: "multilayer_black",
    22: "multilayer_cpu",
    23: "multilayer_cpu_black",
    24: "multilayer_heart",
    25: "multilayer_heart_black",
    26: "multilayer_lizzard",
    27: "multilayer_lizzard_black",
    28: "multilayer_ring",
    29: "multilayer_ring_black",
    30: "multilayer_skull",
    31: "multilayer_skull_black",
    32: "multilayer_spider",
    33: "multilayer_spider_black",
    34: "multilayer_spiral",
    35: "multilayer_spiral_black",
    36: "multilayer_target",
    37: "multilayer_target_black",
    38: "multilayer_x_sign",
    39: "multilayer_x_sign_black",
}

TEETH_APPEARANCES = {
    0: "teeth_001",
    1: "teeth_007__silver",
    2: "teeth_003__gold",
    3: "teeth_002__cooper",
    4: "teeth_006__pink",
}

EYELASH_COLORS = {
    selection: f"eyelashes__{color}"
    for selection, color in HAIR_COLORS.items()
}

NAIL_MESHES = {
    BodyFrame.FEMALE: {
        "short": {
            "left": "base\\characters\\common\\player_base_bodies\\player_female_average\\arms_hq\\nails\\a0_000_pwa_base__nails_l.mesh",
            "right": "base\\characters\\common\\player_base_bodies\\player_female_average\\arms_hq\\nails\\a0_000_pwa_base__nails_r.mesh",
        },
        "long": {
            "left": "base\\characters\\common\\player_base_bodies\\player_female_average\\arms_hq\\nails\\a0_000_pwa_base__nails_l_long.mesh",
            "right": "base\\characters\\common\\player_base_bodies\\player_female_average\\arms_hq\\nails\\a0_000_pwa_base__nails_r_long.mesh",
        },
    },
    BodyFrame.MALE: {
        "short": {
            "left": "base\\characters\\common\\player_base_bodies\\player_man_average\\arms_hq\\nails\\a0_000_pma_base__nails_l.mesh",
            "right": "base\\characters\\common\\player_base_bodies\\player_man_average\\arms_hq\\nails\\a0_000_pma_base__nails_r.mesh",
        },
        "long": {
            "left": "base\\characters\\common\\player_base_bodies\\player_man_average\\arms_hq\\nails\\a0_000_pma_base__nails_l_long.mesh",
            "right": "base\\characters\\common\\player_base_bodies\\player_man_average\\arms_hq\\nails\\a0_000_pma_base__nails_r_long.mesh",
        },
    },
}
EYE_MAKEUP_COLORS = {
    1: "black",
    2: "blue",
    3: "gold",
    4: "green",
    5: "pink",
    6: "red",
    7: "violet",
    8: "white",
    9: "yellow",
    10: "orange",
    11: "teal",
    12: "grey",
    13: "brown",
    14: "neon_yellow",
}
CHEEK_MAKEUP_COLORS = {
    1: "cheeks_brown_", 2: "cheeks_pink_", 3: "cheeks_red_",
    4: "cheeks_goldenbrown_", 5: "cheeks_peach_", 6: "cheeks_raspberry_",
    7: "cheeks_magenta_", 8: "cheeks_green_",
}
FRECKLE_MAKEUP_COLORS = {
    1: ("frecles_brown_01", "frecles_brown_04", "frecles_brown_07", "frecles_brown_10"),
    2: ("frecles_brown_02", "frecles_brown_05", "frecles_brown_08", "frecles_brown_11"),
    3: ("frecles_brown_03", "frecles_brown_06", "frecles_brown_09", "frecles_brown_12"),
    4: ("frecles_black_01", "frecles_black_02", "frecles_black_03", "frecles_black_04"),
}


def cheek_makeup_appearance(style: int, color: int) -> str:
    """Return the exact combined vanilla CC appearance for choices 01-14.

    The game presents these as one selector, but 01-04 are freckles using a
    four-color matrix and 05-14 are cheek makeup using an eight-color prefix.
    """
    if 1 <= style <= 4:
        try:
            return FRECKLE_MAKEUP_COLORS[color][style - 1]
        except KeyError as exc:
            raise ValueError(
                f"Cheek/freckle style {style:02d} supports colors 1-4; got {color}"
            ) from exc
    if 5 <= style <= 14:
        try:
            return f"{CHEEK_MAKEUP_COLORS[color]}{style:02d}"
        except KeyError as exc:
            raise ValueError(
                f"Cheek makeup style {style:02d} supports colors 1-8; got {color}"
            ) from exc
    raise ValueError(f"Cheek makeup style must be Off or 1-14; got {style}")
LIP_MAKEUP_COLORS = {
    1: "black", 2: "blue", 3: "gold", 4: "green", 5: "pink",
    6: "red", 7: "violet", 8: "white", 9: "yellow", 10: "peach",
    11: "burgundy", 12: "brown", 13: "scarlet", 14: "pastel_pink",
}
NAIL_COLORS = {
    1: "beige",
    2: "01_all_brown__multilayer",
    3: "01_all_crimson__multilayer",
    4: "01_all_gradient_black_red__multilayer",
    5: "01_all_gradient_gold__multilayer",
    6: "01_all_gradient_turquoise__multilayer",
    7: "01_all_green__multilayer",
    8: "01_all_pink__multilayer",
    9: "01_all_purple__multilayer",
    10: "01_all_red__multilayer",
    11: "01_all_white__multilayer",
    12: "01_all_yellow__multilayer",
    13: "01_black_gold__multilayer",
    14: "01_blue_silver__multilayer",
    15: "01_chrome_and_black__multilayer",
    16: "01_chrome_and_white__multilayer",
    17: "01_chrome_strap__multilayer",
    18: "01_color_end__multilayer",
    19: "01_five_colors__multilayer",
    20: "01_gradient_chrome__multilayer",
    21: "01_green_heart__multilayer",
    22: "01_ragged_black__multilayer",
    23: "01_ragged_pink__multilayer",
    24: "01_red_gold__multilayer",
    25: "01_red_heart__multilayer",
    26: "01_white_strap__multilayer",
    27: "01_zyzag__multilayer",
    28: "02_blue__multilayer",
    29: "02_default_02__multilayer",
    30: "02_default__multilayer",
    31: "02_fire__multilayer",
    32: "03_default__multilayer",
    33: "01_all_black__multilayer",
    34: "beige_dark",
    35: "checker",
    36: "dots_01",
    37: "gray_light",
}

MALE_HAIR_STYLES: dict[int, dict[str, str]] = {
    38: {
        "mesh": (
            "base\\characters\\common\\hair\\hh_045_ma__short_spiked\\"
            "hh_045_ma__short_spiked.mesh"
        ),
        "shadow": (
            "base\\characters\\common\\hair\\shadow_meshes\\"
            "hh_045_pma__short_spiked_shadow.mesh"
        ),
    },
}

MALE_BLEMISH_COLORS = {
    1: "pimples__brown_02",
    2: "pimples__brown_01",
    3: "pimples__black_02",
    4: "pimples__black_01",
    5: "pimples__red_02",
    6: "pimples__red_01",
}

FEMALE_HAIR_STYLES: dict[int, dict[str, Any]] = {
    4: {
        "meshes": (
            (
                "hh_hair",
                "base\\characters\\common\\hair\\hh_089_ma__thompson\\"
                "hh_089_wa__thompson_common.mesh",
            ),
        ),
        "shadow": "base\\characters\\common\\hair\\shadow_meshes\\hh_062_ma__slick_back_shadow_npc.mesh",
        "controller": None,
    },
    6: {
        "meshes": (
            (
                "hh_hair",
                "base\\characters\\common\\hair\\hh_078_wa__evelyn\\"
                "hh_078_wa__evelyn_common.mesh",
            ),
        ),
        "shadow": (
            "base\\characters\\common\\hair\\shadow_meshes\\"
            "hh_078_wa__evelyn_shadow_npc.mesh"
        ),
        "controller": {
            "name": "hair_dangle",
            "rig": (
                "base\\characters\\common\\hair\\hh_078_wa__evelyn\\"
                "hh_078_wa__evelyn_dangle_skeleton.rig"
            ),
            "graph": (
                "base\\characters\\common\\hair\\hh_078_wa__evelyn\\"
                "hh_078_wa__evelyn_dangle.animgraph"
            ),
        },
    },
    8: {
        "meshes": (
            (
                "hh_hair",
                "base\\characters\\common\\hair\\hh_036_ma__high_tight\\"
                "hh_036_wa__high_tight.mesh",
            ),
        ),
        "shadow": "base\\characters\\common\\hair\\shadow_meshes\\hh_045_ma__short_spiked_shadow_npc.mesh",
        "controller": None,
    },
    11: {
        "meshes": (
            (
                "hh_hair",
                "base\\characters\\common\\hair\\hh_091_wa__dakota\\"
                "hh_091_wa__dakota.mesh",
            ),
            (
                "hh_hair_braid",
                "base\\characters\\common\\hair\\hh_091_wa__dakota\\"
                "hh_091_wa__dakota_braid.mesh",
            ),
            (
                "hh_hair_band",
                "base\\characters\\common\\hair\\hh_091_wa__dakota\\"
                "hh_091_wa__dakota_braid_band.mesh",
            ),
        ),
        "shadow": "base\\characters\\common\\hair\\shadow_meshes\\hh_091_pwa__dakota_shadow.mesh",
        "controller": {
            "name": "hair_dangle",
            "rig": (
                "base\\characters\\common\\hair\\hh_091_wa__dakota\\"
                "hh_091_wa__dakota_dangle_skeleton.rig"
            ),
            "graph": (
                "base\\characters\\common\\hair\\hh_091_wa__dakota\\"
                "hh_091_wa__dakota_dangle_skeleton.animgraph"
            ),
        },
    },
    24: {
        "meshes": (
            (
                "hh_hair",
                "base\\characters\\common\\hair\\hh_064_wa__bob_fringe\\"
                "hh_064_wa__bob_fringe.mesh",
            ),
        ),
        "shadow": "base\\characters\\common\\hair\\shadow_meshes\\hh_078_wa__evelyn_shadow_npc.mesh",
        "controller": {
            "name": "hair_dangle",
            "rig": (
                "base\\characters\\common\\hair\\hh_064_wa__bob_fringe\\"
                "hh_064_wa__bob_fringe_dangle_skeleton.rig"
            ),
            "graph": (
                "base\\characters\\common\\hair\\hh_064_wa__bob_fringe\\"
                "hh_064_wa__bob_fringe_dangle.animgraph"
            ),
        },
    },
    33: {
        "meshes": (
            (
                "hh_hair",
                "base\\characters\\common\\hair\\hh_121_wa__t_bug\\"
                "hh_121_wa__t_bug_common.mesh",
            ),
        ),
        "shadow": "base\\characters\\common\\hair\\shadow_meshes\\hh_121_wa__t_bug_shadow_npc.mesh",
        "controller": None,
    },
    42: {
        "meshes": (
            (
                "hh_hair",
                "base\\characters\\common\\hair\\hh_103_ma__maelstrom_spikes\\"
                "hh_103_wa__common_spikes.mesh",
            ),
        ),
        "shadow": "base\\characters\\common\\hair\\shadow_meshes\\hh_103_ma__maelstrom_spikes_shadow_npc.mesh",
        "controller": None,
    },
}

# The small dictionaries above document the original vertical-slice fixtures.
# Production selection uses the complete frame-specific native catalog serialized
# from the game's player hair appearance resources.
_VANILLA_HAIR_STYLES = load_hair_styles()
FEMALE_HAIR_STYLES = _VANILLA_HAIR_STYLES["female"]
MALE_HAIR_STYLES = _VANILLA_HAIR_STYLES["male"]

FEMALE_HAIR_MESHES = {
    style: definition["meshes"][0][1]
    for style, definition in FEMALE_HAIR_STYLES.items()
}
FEMALE_HAIR_SHADOW_MESHES = {
    style: definition["shadow"]
    for style, definition in FEMALE_HAIR_STYLES.items()
}


def female_hair_resource_paths(hairstyle: int) -> tuple[str, ...]:
    definition = FEMALE_HAIR_STYLES.get(hairstyle)
    if definition is None:
        raise ValueError(f"No verified feminine hairstyle definition for {hairstyle}")
    resources = [mesh for _, mesh in definition["meshes"]]
    if definition["shadow"] is not None:
        resources.append(definition["shadow"])
    controller = definition["controller"]
    if controller is not None:
        resources.extend((controller["rig"], controller["graph"]))
    return tuple(resources)


def hair_color_appearance(
    frame: BodyFrame, hairstyle: int, hair_color: int
) -> str:
    catalog = FEMALE_HAIR_STYLES if frame is BodyFrame.FEMALE else MALE_HAIR_STYLES
    definition = catalog[hairstyle]
    return f"{HAIR_COLORS[hair_color]}{definition['color_suffix']}"
FEMALE_BODY_MESHES = {
    "default": (
        "tutorial\\npv\\your_female_character\\body\\"
        "t0_000_pwa_base__full.mesh"
    ),
    "small": (
        "base\\characters\\common\\player_base_bodies\\player_female_average\\"
        "t0_000_pwa_base__full_breast_small.mesh"
    ),
    "big": (
        "base\\characters\\common\\player_base_bodies\\player_female_average\\"
        "t0_000_pwa_base__full_breast_big.mesh"
    ),
}
FEMALE_SEAMFIX = (
    "base\\characters\\common\\player_base_bodies\\player_female_average\\"
    "t0_000_pwa_base__full_seamfix.mesh"
)
FEMALE_NPC_BODY_MESH = (
    "base\\characters\\common\\base_bodies\\woman_average\\"
    "t0_000_wa_base__full.mesh"
)
FEMALE_NPC_BODY_REMOVED_COMPONENTS = {
    "an0__arm_right",
    "an0__arm_left",
    "t0_000_pwa_base__full_seamfix",
}
BODY_TATTOO_MESH_INDEX = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 1,
    7: 1,
}
BODY_TATTOO_APPEARANCE_SUFFIX = {
    1: "",
    2: "",
    3: "",
    4: "",
    5: "",
    6: "_02",
    7: "_03",
}
FEMALE_BODY_TATTOOS = {
    "default": {
        selection: (
            "base\\characters\\common\\player_base_bodies\\player_female_average\\tattoos\\"
            f"tx_000_pwa_base__full_tattoo_{mesh_index:02d}.mesh"
        )
        for selection, mesh_index in BODY_TATTOO_MESH_INDEX.items()
    },
    "big": {
        # CDPR's breast-big tattoo meshes expose only the base skin appearance.
        # Creator choices 6/7 require _02/_03, so retain the normal mesh that
        # actually owns those materials (verified in the vanilla mesh catalog).
        selection: (
            "base\\characters\\common\\player_base_bodies\\player_female_average\\tattoos\\"
            + (
                f"tx_000_pwa_base__full_tattoo_{mesh_index:02d}_breast_big.mesh"
                if BODY_TATTOO_APPEARANCE_SUFFIX[selection] == ""
                else f"tx_000_pwa_base__full_tattoo_{mesh_index:02d}.mesh"
            )
        )
        for selection, mesh_index in BODY_TATTOO_MESH_INDEX.items()
    },
}
MALE_BODY_TATTOOS = {
    selection: (
        "base\\characters\\common\\player_base_bodies\\player_man_average\\tattoos\\"
        f"tx_000_pma_base__full_tattoo_{mesh_index:02d}.mesh"
    )
    for selection, mesh_index in BODY_TATTOO_MESH_INDEX.items()
}
FEMALE_BIG_NIPPLES = {
    selection: (
        "base\\characters\\common\\player_base_bodies\\player_female_average\\genitals\\"
        "i0_000_pwa_base__nipple_breast_big.mesh"
    )
    for selection in range(1, 4)
}
# The source nipple mesh exposes all three creator materials. NPV Studio bakes
# chest-specific geometry into that material-complete mesh instead of using
# CDPR's big-breast static mesh, which omits the __02/__03 appearances.
FEMALE_NIPPLE_APPEARANCE_SUFFIX = {1: "", 2: "__02", 3: "__03"}
FEMALE_DUAL_BODY_COMPONENTS = {
    "clothing_safe": "t0_body",
    "clothing_safe_alternate": "t0_body_clothing_safe",
    "nude_large": "t0_body_nude_large",
    "small": "t0_body_small",
    "tattoo_clothing_safe": "tx_000_pwa_base__full_tattoo_03",
    "tattoo_nude_large": "tx_000_pwa_base__full_tattoo_03_nude_large",
    "nipples_nude_large": "i0_000_pwa_base__nipple_nude_large",
    "nipples_clothing_safe": "i0_000_pwa_base__nipple_clothing_safe",
    "nipples_selected": "i0_000_pwa_base__nipple",
    "nipples_alternate": "i0_000_pwa_base__nipple_alternate",
}
GENERATED_BODY_DETAIL_COMPONENTS = {
    "t0_body_scars",
    "t0_body_scars_clothing_safe",
    "t0_body_scars_nude_large",
    "t0_genitals",
    "t0_pubic_hair",
}


def _female_body_variants(selected_chest: str) -> list[tuple[str, str, bool]]:
    """Return stable normal/big toggles plus the small torso when selected."""
    variants = [
        ("default", FEMALE_DUAL_BODY_COMPONENTS["clothing_safe"], selected_chest == "default"),
        ("big", FEMALE_DUAL_BODY_COMPONENTS["nude_large"], selected_chest == "big"),
    ]
    if selected_chest == "small":
        variants.append(("small", FEMALE_DUAL_BODY_COMPONENTS["small"], True))
    return variants


def _female_variant_suffix(chest: str, selected_chest: str) -> str:
    # Component names are role-based and stable across presets so AMM users can
    # always find the same normal/big toggle pair.
    if chest == "default":
        return ""
    if chest == "big":
        return "_nude_large"
    return f"_{chest}"

SCAR_SKIN_APPEARANCES = {
    1: "scar__01_ca_pale",
    2: "scar__01_ca_pale",
    3: "scar__02_ca_limestone",
    4: "scar__02_ca_limestone",
    5: "scar__03_ca_senna",
    6: "scar__03_ca_senna",
    7: "scar__03_ca_senna",
    8: "scar__03_ca_senna",
    9: "scar__04_ca_almond",
    10: "scar__04_ca_almond",
    11: "scar__05_bl_espresso",
    12: "scar__06_bl_black",
}


def _female_tattoo_component_names(selection: int) -> tuple[str, str]:
    if selection == 0:
        return (
            "tx_000_pwa_base__full_tattoo_off",
            "tx_000_pwa_base__full_tattoo_off_nude_large",
        )
    mesh_index = BODY_TATTOO_MESH_INDEX[selection]
    variant = "" if selection <= 5 else f"_choice_{selection:02d}"
    base = f"tx_000_pwa_base__full_tattoo_{mesh_index:02d}{variant}"
    return base, f"{base}_nude_large"


FEMALE_GENERATED_TATTOO_COMPONENTS = {
    name
    for selection in set(FEMALE_BODY_TATTOOS["default"]) | set(FEMALE_BODY_TATTOOS["big"])
    for base_name in _female_tattoo_component_names(selection)[:1]
    for name in (base_name, f"{base_name}_nude_large", f"{base_name}_clothing_safe")
}

# Appearance Creator Mod classifies components by these name prefixes. Empty
# components are deliberately disabled and use resource path 0 until the user
# assigns a mesh through ACM.
ACM_EMPTY_SLOT_LAYOUT: dict[str, tuple[str, int]] = {
    "face": ("hx_", 5),
    "head": ("h1_", 5),
    "torso": ("t2_", 5),
    "legs": ("l1_", 5),
    "item": ("i1_", 5),
    "hands": ("g1_", 2),
    "arms": ("a0_", 2),
    "feet": ("s1_", 2),
}
ACM_EMPTY_SLOT_NAMES = {
    f"{prefix}npvstudio_{category}_slot_{index:02d}"
    for category, (prefix, count) in ACM_EMPTY_SLOT_LAYOUT.items()
    for index in range(1, count + 1)
}

OFF_COMPONENTS = {
    "hx_makeup_freckles": "cheek makeup / freckles are off",
    "hx_makeup_lips_01": "lip makeup is off",
    "i1_earring": "piercings are off",
    "h0_tattoo": "facial tattoos are off",
    "h0x001__personal_slot_decal": "tutorial-only facial decal is not in the preset",
    "i1_088_wa_full__gun_harness0222": "tutorial business gun harness is not part of the NPV",
    "i1_088_wa_full__gun_harness_pistol": "tutorial business holstered pistol is not part of the NPV",
}


def normalize_default_app_appearance(document: dict[str, Any]) -> dict[str, Any]:
    """Keep the starter/casual appearance and publish it as ``default``."""
    appearances = document["Data"]["RootChunk"].get("appearances")
    if not isinstance(appearances, list):
        raise ValueError("The app document has no appearances list")

    kept: list[dict[str, Any]] = []
    renamed = 0
    removed: list[str] = []
    for appearance in appearances:
        data = appearance.get("Data")
        name = str(_value(data.get("name"))) if isinstance(data, dict) else ""
        if name == "business":
            removed.append(name)
            continue
        if name in {"casual", "default"}:
            _set_value(data, "name", "default")
            renamed += 1
        kept.append(appearance)
    if renamed != 1:
        raise ValueError(
            f"Expected one casual/default app appearance, found {renamed}"
        )
    document["Data"]["RootChunk"]["appearances"] = kept
    return {"published": "default", "removed": removed}


def normalize_default_entity_appearance(document: dict[str, Any]) -> dict[str, Any]:
    """Publish exactly one AMM-visible entity appearance named ``default``."""
    root = document["Data"]["RootChunk"]
    appearances = root.get("appearances")
    if not isinstance(appearances, list):
        raise ValueError("The entity document has no appearances list")

    selected: list[dict[str, Any]] = []
    removed: list[str] = []
    for appearance in appearances:
        appearance_name = str(_value(appearance.get("appearanceName")))
        public_name = str(_value(appearance.get("name")))
        if appearance_name not in {"casual", "default"}:
            removed.append(public_name or appearance_name)
            continue
        _set_value(appearance, "appearanceName", "default")
        _set_value(appearance, "name", "default")
        selected.append(appearance)
    if len(selected) != 1:
        raise ValueError(
            f"Expected one casual/default entity appearance, found {len(selected)}"
        )
    root["appearances"] = selected
    return {"published": "default", "removed": removed}


def _fnv1a64(value: str) -> int:
    result = 0xCBF29CE484222325
    for byte in value.encode("utf-8"):
        result ^= byte
        result = (result * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return result


def _value(node: dict[str, Any] | None) -> Any:
    return None if not node else node.get("$value")


def _set_value(component: dict[str, Any], field: str, value: Any) -> None:
    node = component.get(field)
    if not isinstance(node, dict) or "$value" not in node:
        raise ValueError(f"Component {component.get('name')} has no editable {field}")
    node["$value"] = value


def _set_mesh_value(component: dict[str, Any], value: Any) -> None:
    mesh = component.get("mesh")
    depot_path = mesh.get("DepotPath") if isinstance(mesh, dict) else None
    if not isinstance(depot_path, dict) or "$value" not in depot_path:
        raise ValueError(f"Component {component.get('name')} has no editable mesh DepotPath")
    depot_path["$value"] = value
    depot_path["$storage"] = "uint64" if str(value).isdigit() else "string"


def _set_resource_value(component: dict[str, Any], field: str, value: str) -> None:
    resource = component.get(field)
    depot_path = resource.get("DepotPath") if isinstance(resource, dict) else None
    if not isinstance(depot_path, dict) or "$value" not in depot_path:
        raise ValueError(f"Component {component.get('name')} has no editable {field} DepotPath")
    depot_path["$value"] = value
    depot_path["$storage"] = "string"


def _walk_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_dicts(value)


def _rewrite_component_bindings(
    document: dict[str, Any], component_name: str, value: str
) -> dict[str, int]:
    """Rewrite inline and shared REDengine bindings belonging to a named component."""
    fields = ("parentTransform", "skinning")
    referenced: dict[str, set[str]] = {field: set() for field in fields}
    updates = {field: 0 for field in fields}

    for component in _walk_dicts(document):
        if _component_name(component) != component_name:
            continue
        for field in fields:
            binding = component.get(field)
            if not isinstance(binding, dict):
                raise ValueError(f"Component {component_name} has no {field} binding")
            data = binding.get("Data")
            if isinstance(data, dict):
                bind_name = data.get("bindName")
                if not isinstance(bind_name, dict) or "$value" not in bind_name:
                    raise ValueError(f"Component {component_name} has no editable {field} bindName")
                bind_name["$value"] = value
                updates[field] += 1
            elif "HandleRefId" in binding:
                referenced[field].add(str(binding["HandleRefId"]))
            else:
                raise ValueError(f"Component {component_name} has an invalid {field} binding")

    for node in _walk_dicts(document):
        handle_id = str(node.get("HandleId")) if "HandleId" in node else None
        if handle_id is None:
            continue
        for field in fields:
            if handle_id not in referenced[field]:
                continue
            data = node.get("Data")
            bind_name = data.get("bindName") if isinstance(data, dict) else None
            if isinstance(bind_name, dict) and "$value" in bind_name:
                bind_name["$value"] = value
                updates[field] += 1

    missing = [field for field, count in updates.items() if count == 0]
    if missing:
        raise ValueError(
            f"Component {component_name} does not own the expected bindings: "
            + ", ".join(missing)
        )
    return updates


def _rewrite_component_binding_field(
    document: dict[str, Any], component_name: str, field: str, value: str
) -> int:
    referenced: set[str] = set()
    updates = 0
    for component in _walk_dicts(document):
        if _component_name(component) != component_name:
            continue
        binding = component.get(field)
        if not isinstance(binding, dict):
            raise ValueError(f"Component {component_name} has no {field} binding")
        data = binding.get("Data")
        if isinstance(data, dict):
            bind_name = data.get("bindName")
            if not isinstance(bind_name, dict) or "$value" not in bind_name:
                raise ValueError(f"Component {component_name} has no editable {field} bindName")
            bind_name["$value"] = value
            updates += 1
        elif "HandleRefId" in binding:
            referenced.add(str(binding["HandleRefId"]))
        else:
            raise ValueError(f"Component {component_name} has an invalid {field} binding")

    for node in _walk_dicts(document):
        if str(node.get("HandleId")) not in referenced:
            continue
        data = node.get("Data")
        bind_name = data.get("bindName") if isinstance(data, dict) else None
        if isinstance(bind_name, dict) and "$value" in bind_name:
            bind_name["$value"] = value
            updates += 1
    if updates == 0:
        raise ValueError(f"Component {component_name} has no editable {field} binding")
    return updates


def _component_name(component: dict[str, Any]) -> str | None:
    return _value(component.get("name"))


STARTER_OUTFIT_SLOT_PREFIXES = {
    "inner_torso": "t1_",
    "legs": "l1_",
    "feet": "s1_",
}


def _appearance_component_tables(
    appearance_data: dict[str, Any],
) -> list[tuple[str, list[dict[str, Any]]]]:
    components = appearance_data.get("components")
    if not isinstance(components, list):
        raise ValueError("Appearance has no editable component table")
    tables = [("components", components)]
    compiled = appearance_data.get("compiledData")
    compiled_data = compiled.get("Data") if isinstance(compiled, dict) else None
    chunks = compiled_data.get("Chunks") if isinstance(compiled_data, dict) else None
    if isinstance(chunks, list):
        tables.append(("compiledData", chunks))
    return tables


def apply_default_starter_outfit(
    appearance_data: dict[str, Any], character: CharacterConfig
) -> dict[str, dict[str, Any]]:
    """Replace the tutorial casual clothes with V's verified vanilla outfit."""
    appearance_name = str(_value(appearance_data.get("name")))
    if appearance_name not in {"casual", "default"}:
        return {}

    outfit_data = load_game_data(character.game_version)["starter_outfit"]
    garments = outfit_data["body_frames"][character.body_frame.value]
    tables = _appearance_component_tables(appearance_data)
    direct_components = tables[0][1]
    resolved: dict[str, dict[str, Any]] = {}

    for garment in garments:
        slot = str(garment["slot"])
        prefix = STARTER_OUTFIT_SLOT_PREFIXES[slot]
        candidates = [
            component
            for component in direct_components
            if (
                (name := str(_component_name(component) or "")).startswith(prefix)
                and "npvstudio" not in name
                and "shadow" not in name.casefold()
                and isinstance(component.get("mesh"), dict)
            )
        ]
        if not candidates:
            if character.output.mode is BuildMode.FINAL:
                raise ValueError(
                    f"Default appearance has no editable {slot} clothing component"
                )
            return {}
        if len(candidates) != 1:
            names = [str(_component_name(component)) for component in candidates]
            raise ValueError(
                f"Default appearance has ambiguous {slot} clothing components: {names}"
            )

        component_name = str(_component_name(candidates[0]))
        for table_name, table in tables:
            matches = [
                component
                for component in table
                if _component_name(component) == component_name
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"{table_name} has {len(matches)} copies of starter component "
                    f"{component_name}; expected one"
                )
            component = matches[0]
            _set_mesh_value(component, str(garment["mesh_path"]))
            _set_value(component, "meshAppearance", str(garment["mesh_appearance"]))
            component["chunkMask"] = str(garment["chunk_mask"])
            _set_component_enabled(component, True)

        resolved[slot] = {
            "component": component_name,
            "item_id": garment["item_id"],
            "mesh": garment["mesh_path"],
            "appearance": garment["mesh_appearance"],
            "chunk_mask": str(garment["chunk_mask"]),
        }
    return resolved


def _remove_compiled_components(
    appearance_data: dict[str, Any], component_names: set[str]
) -> list[str]:
    """Remove stale compiled component chunks and rebuild their index-to-CRUID map."""
    compiled = appearance_data.get("compiledData")
    compiled_data = compiled.get("Data") if isinstance(compiled, dict) else None
    chunks = compiled_data.get("Chunks") if isinstance(compiled_data, dict) else None
    if not isinstance(chunks, list):
        return []

    removed = [
        str(name)
        for chunk in chunks
        if (name := _component_name(chunk)) in component_names
    ]
    if not removed:
        return []

    kept = [chunk for chunk in chunks if _component_name(chunk) not in component_names]
    compiled_data["Chunks"] = kept
    cruid_dict = compiled_data.get("CruidDict")
    if isinstance(cruid_dict, dict):
        rebuilt: dict[str, str] = {}
        for index, chunk in enumerate(kept):
            cruid = chunk.get("id")
            if cruid is None:
                raise ValueError(
                    f"Compiled component at index {index} has no CRUID after filtering"
                )
            rebuilt[str(index)] = str(cruid)
        compiled_data["CruidDict"] = rebuilt
    return removed


def _insert_compiled_components_after(
    appearance_data: dict[str, Any],
    anchor_name: str,
    components: list[dict[str, Any]],
) -> bool:
    """Mirror new components into compiledData so AMM preserves their section order."""
    compiled = appearance_data.get("compiledData")
    compiled_data = compiled.get("Data") if isinstance(compiled, dict) else None
    chunks = compiled_data.get("Chunks") if isinstance(compiled_data, dict) else None
    if not isinstance(chunks, list):
        return False

    anchor_index = next(
        (
            index
            for index, chunk in enumerate(chunks)
            if _component_name(chunk) == anchor_name
        ),
        None,
    )
    if anchor_index is None:
        raise ValueError(f"Compiled component table has no {anchor_name} anchor")

    chunks[anchor_index + 1 : anchor_index + 1] = deepcopy(components)
    cruid_dict = compiled_data.get("CruidDict")
    if isinstance(cruid_dict, dict):
        rebuilt: dict[str, str] = {}
        for index, chunk in enumerate(chunks):
            cruid = chunk.get("id")
            if cruid is None:
                raise ValueError(
                    f"Compiled component at index {index} has no CRUID after insertion"
                )
            rebuilt[str(index)] = str(cruid)
        compiled_data["CruidDict"] = rebuilt
    return True


def _shared_binding_reference(component: dict[str, Any], field: str) -> dict[str, str]:
    binding = component.get(field)
    if not isinstance(binding, dict):
        raise ValueError(f"Component {_component_name(component)} has no {field} binding")
    handle_id = binding.get("HandleRefId", binding.get("HandleId"))
    if handle_id is None:
        raise ValueError(f"Component {_component_name(component)} has no shareable {field} handle")
    return {"HandleRefId": str(handle_id)}


def _body_overlay_component(
    body: dict[str, Any], *, name: str, mesh: str, appearance: str, shadows: bool
) -> dict[str, Any]:
    overlay = deepcopy(body)
    _set_value(overlay, "name", name)
    _set_mesh_value(overlay, mesh)
    _set_value(overlay, "meshAppearance", appearance)
    overlay["id"] = str(_fnv1a64(f"npv_studio:{name}"))
    overlay["parentTransform"] = _shared_binding_reference(body, "parentTransform")
    overlay["skinning"] = _shared_binding_reference(body, "skinning")
    overlay["autoHideDistance"] = 200 if shadows else 0
    overlay["castLocalShadows"] = "Always" if shadows else "Never"
    overlay["castShadows"] = "Never"
    overlay["forceLODLevel"] = -1
    overlay["LODMode"] = "AlwaysVisible"
    return overlay


def _set_component_enabled(component: dict[str, Any], enabled: bool) -> None:
    """Set REDengine component state while preserving WolvenKit's JSON shape."""
    current = component.get("isEnabled")
    if isinstance(current, dict) and "$value" in current:
        current["$value"] = enabled
    else:
        component["isEnabled"] = 1 if enabled else 0


def _body_variant_component(
    body: dict[str, Any], *, name: str, mesh: str, appearance: str, enabled: bool
) -> dict[str, Any]:
    """Clone a torso component as an independently toggleable AMM body option."""
    variant = deepcopy(body)
    _set_value(variant, "name", name)
    _set_mesh_value(variant, mesh)
    _set_value(variant, "meshAppearance", appearance)
    variant["id"] = str(_fnv1a64(f"npv_studio:{name}"))
    variant["parentTransform"] = _shared_binding_reference(body, "parentTransform")
    variant["skinning"] = _shared_binding_reference(body, "skinning")
    _set_component_enabled(variant, enabled)
    return variant


def _body_detail_components(
    body: dict[str, Any], character: CharacterConfig, *, skin_base: str
) -> list[dict[str, Any]]:
    """Compile body scars, genitals and pubic hair into concrete mesh components."""
    selection = character.appearance
    frame = character.body_frame
    components: list[dict[str, Any]] = []
    if selection.body_scars:
        scar_variants = (
            _female_body_variants(selection.chest)
            if frame is BodyFrame.FEMALE
            else [("default", "t0_body", True)]
        )
        for chest, _body_name, enabled in scar_variants:
            suffix = _female_variant_suffix(chest, selection.chest) if frame is BodyFrame.FEMALE else ""
            scars = _body_overlay_component(
                body,
                name=f"t0_body_scars{suffix}",
                mesh=body_scar_depot_path(frame, chest),
                appearance=SCAR_SKIN_APPEARANCES[selection.skin_tone],
                shadows=False,
            )
            scars["chunkMask"] = str(BODY_SCAR_CHUNK_MASKS[selection.body_scars])
            _set_component_enabled(scars, enabled)
            components.append(scars)

    genital_mesh = genital_depot_path(
        frame, selection.genitals, selection.penis_size
    )
    if genital_mesh is not None:
        genitals = _body_overlay_component(
            body,
            name="t0_genitals",
            mesh=genital_mesh,
            appearance=skin_base,
            shadows=False,
        )
        genitals["chunkMask"] = "9223372036854775807"
        penis_selected = selection.genitals.startswith("penis")
        _set_component_enabled(genitals, not penis_selected)
        components.append(genitals)

    if selection.pubic_hair_style:
        pubic_mesh = pubic_hair_depot_path(
            frame, selection.genitals, selection.penis_size
        )
        if pubic_mesh is None:
            raise ValueError("Pubic hair requires a selected genital geometry")
        pubic = _body_overlay_component(
            body,
            name="t0_pubic_hair",
            mesh=pubic_mesh,
            appearance=pubic_hair_appearance(
                selection.pubic_hair_style, selection.pubic_hair_color
            ),
            shadows=True,
        )
        pubic["chunkMask"] = "9223372036854775807"
        _set_component_enabled(pubic, not selection.genitals.startswith("penis"))
        components.append(pubic)
    return components


def _head_overlay_component(
    template: dict[str, Any], *, name: str, mesh: str, appearance: str,
    chunk_mask: int | str | None = None
) -> dict[str, Any]:
    """Clone a face-bound component with a deterministic local baked-mesh reference."""
    component = deepcopy(template)
    _set_value(component, "name", name)
    _set_mesh_value(component, str(_fnv1a64(mesh)))
    _set_value(component, "meshAppearance", appearance)
    component["id"] = str(_fnv1a64(f"npv_studio:head:{name}"))
    component["parentTransform"] = _shared_binding_reference(template, "parentTransform")
    component["skinning"] = _shared_binding_reference(template, "skinning")
    component["chunkMask"] = str(
        9223372036854775807 if chunk_mask is None else chunk_mask
    )
    _set_component_enabled(component, True)
    return component


def _local_head_mesh(frame: BodyFrame, stem: str) -> str:
    return (
        f"tutorial\\npv\\your_{frame.value}_character\\head\\"
        f"{stem}.mesh"
    )


def _head_visual_components(
    template: dict[str, Any], character: CharacterConfig, *, skin_base: str
) -> list[dict[str, Any]]:
    """Compile every currently catalogued face-layer choice into exact components."""
    frame = character.body_frame
    code = frame_code(frame)
    selection = character.appearance
    components: list[dict[str, Any]] = []

    def add(name: str, stem: str, appearance: str, chunk: int | None = None) -> None:
        components.append(
            _head_overlay_component(
                template,
                name=name,
                mesh=_local_head_mesh(frame, stem),
                appearance=appearance,
                chunk_mask=chunk,
            )
        )

    if selection.cyberware:
        definition = CYBERWARE[selection.cyberware]
        stem = f"hx_000_{code}_c__basehead_{definition['mesh']}"
        add("h0_cyberware_face", stem, str(definition[frame.value]), definition["chunk_mask"])
    if frame is BodyFrame.MALE and selection.eyebrows:
        add(
            "heb_eyebrows",
            f"heb_000_{code}_c__basehead",
            f"{HAIR_COLORS[selection.eyebrow_color]}__{selection.eyebrows:02d}",
        )
    # The creator's eyelash selector is a material choice on an eyelash-only
    # chunk of the already baked eye geometry.  It is not part of eye color.
    add(
        "hel_eyelashes",
        f"he_000_{code}_c__basehead",
        EYELASH_COLORS[selection.eyelash_color],
        18446744073709551609,
    )
    if frame is BodyFrame.MALE and selection.beard:
        shape = selection.beard
        add(
            "hb_beard_shadow",
            "hb_000_pma_c__basehead_shadowbase_01",
            BEARD_SHADOW_APPEARANCES[shape],
        )
        stems = BEARD_MESHES[shape]
        if len(stems) > 1:
            stem = stems[1]
            local_stem = "hb_000_pma_c__basehead" if stem == "default" else f"hb_000_pma_c__basehead_{stem}"
            add(
                "hb_beard",
                local_stem,
                HAIR_COLORS[selection.beard_color],
                BEARD_STYLE_CHUNK_MASKS[shape][selection.beard_style],
            )
    if selection.facial_scars:
        add(
            "hx_facial_scars",
            f"hx_000_{code}_c__basehead_scars_01",
            "scars_01",
            FACIAL_SCAR_CHUNK_MASKS[selection.facial_scars],
        )
    if selection.facial_tattoos:
        tattoo_mesh = FACIAL_TATTOO_MESHES[selection.facial_tattoos]
        add(
            "h0_tattoo",
            f"hx_000_{code}_c__basehead_{tattoo_mesh}",
            f"{skin_base}{FACIAL_TATTOO_APPEARANCE_SUFFIXES[selection.facial_tattoos]}",
            FACIAL_TATTOO_CHUNK_MASKS[selection.facial_tattoos],
        )
    if selection.eye_makeup:
        add(
            "hx_makeup_eyes",
            f"hx_000_{code}_c__basehead_makeup_eyes_01",
            f"{EYE_MAKEUP_COLORS[selection.eye_makeup_color]}_{selection.eye_makeup:02d}",
        )
    if selection.cheek_makeup:
        add(
            "hx_cheek_makeup",
            f"hx_000_{code}_c__basehead_makeup_freckles_01",
            cheek_makeup_appearance(
                selection.cheek_makeup, selection.cheek_makeup_color
            ),
        )
    if selection.blemishes:
        add(
            "hx_blemishes",
            f"hx_000_{code}_c__basehead_pimples_01",
            MALE_BLEMISH_COLORS[selection.blemish_color],
            {1: None, 2: 1, 3: 2}[selection.blemishes],
        )
    if selection.lip_makeup:
        finish = {"off": "", "default": "", "glossy": "_02", "matte": "_03"}[
            selection.lip_makeup_finish
        ]
        add(
            "hx_makeup_lips_01",
            f"hx_000_{code}_c__basehead_makeup_lips_01",
            f"{LIP_MAKEUP_COLORS[selection.lip_makeup_color]}_{selection.lip_makeup:02d}{finish}",
        )
    if selection.piercings:
        material = PIERCING_COLORS[selection.piercing_color]
        for index, (mesh_number, chunk) in enumerate(PIERCINGS[frame][selection.piercings], 1):
            add(
                f"i1_earring_{index:02d}",
                f"i1_000_{code}_c__basehead_earring_{mesh_number:02d}",
                material,
                chunk,
            )
    return components


def _has_requested_head_visuals(character: CharacterConfig) -> bool:
    selection = character.appearance
    return any(
        (
            True,  # eyelash color always emits an eyelash-only overlay
            character.body_frame is BodyFrame.MALE and selection.eyebrows,
            character.body_frame is BodyFrame.MALE and selection.beard,
            selection.cyberware,
            selection.facial_scars,
            selection.facial_tattoos,
            selection.eye_makeup,
            selection.cheek_makeup,
            selection.blemishes,
            selection.lip_makeup,
            selection.piercings,
        )
    )


def _compiled_component_exists(
    appearance_data: dict[str, Any], component_name: str
) -> bool:
    compiled = appearance_data.get("compiledData")
    data = compiled.get("Data") if isinstance(compiled, dict) else None
    chunks = data.get("Chunks") if isinstance(data, dict) else None
    return isinstance(chunks, list) and any(
        _component_name(chunk) == component_name for chunk in chunks
    )


def _empty_acm_slot_component(
    template: dict[str, Any], *, category: str, prefix: str, index: int
) -> dict[str, Any]:
    name = f"{prefix}npvstudio_{category}_slot_{index:02d}"
    slot = deepcopy(template)
    slot["$type"] = "entSkinnedMeshComponent"
    _set_value(slot, "name", name)
    _set_mesh_value(slot, "0")
    _set_value(slot, "meshAppearance", "default")
    slot["id"] = str(_fnv1a64(f"npv_studio:acm_slot:{name}"))
    slot["parentTransform"] = _shared_binding_reference(template, "parentTransform")
    slot["skinning"] = _shared_binding_reference(template, "skinning")
    slot["chunkMask"] = "9223372036854775807"
    slot["castLocalShadows"] = "Never"
    slot["castShadows"] = "Never"
    slot["forceLODLevel"] = -1
    slot["LODMode"] = "AlwaysVisible"
    _set_component_enabled(slot, False)
    return slot


def _add_empty_acm_slots(
    appearance_data: dict[str, Any], template: dict[str, Any]
) -> list[str]:
    components = appearance_data.get("components")
    if not isinstance(components, list):
        raise ValueError("Appearance has no components list for ACM slots")

    slots = [
        _empty_acm_slot_component(
            template,
            category=category,
            prefix=prefix,
            index=index,
        )
        for category, (prefix, count) in ACM_EMPTY_SLOT_LAYOUT.items()
        for index in range(1, count + 1)
    ]
    anchor_index = next(
        (
            index
            for index, component in enumerate(components)
            if (
                "clothing" in str(_component_name(component) or "").casefold()
                and "=" in str(_component_name(component) or "")
            )
        ),
        len(components) - 1,
    )
    components[anchor_index + 1 : anchor_index + 1] = slots

    compiled = appearance_data.get("compiledData")
    compiled_data = compiled.get("Data") if isinstance(compiled, dict) else None
    chunks = compiled_data.get("Chunks") if isinstance(compiled_data, dict) else None
    if isinstance(chunks, list):
        compiled_anchor = next(
            (
                index
                for index, component in enumerate(chunks)
                if (
                    "clothing" in str(_component_name(component) or "").casefold()
                    and "=" in str(_component_name(component) or "")
                )
            ),
            len(chunks) - 1,
        )
        chunks[compiled_anchor + 1 : compiled_anchor + 1] = deepcopy(slots)
        cruid_dict = compiled_data.get("CruidDict")
        if isinstance(cruid_dict, dict):
            compiled_data["CruidDict"] = {
                str(index): str(component["id"])
                for index, component in enumerate(chunks)
            }
    return [str(_component_name(slot)) for slot in slots]


def _apply_female_hair_style(
    document: dict[str, Any],
    hairstyle: int,
    *,
    hair_color: str | None,
    require_seamfix: bool,
) -> dict[str, Any]:
    definition = FEMALE_HAIR_STYLES.get(hairstyle)
    if definition is None:
        raise ValueError(
            f"No verified feminine hair definition for hairstyle {hairstyle}; "
            f"supported values are {sorted(FEMALE_HAIR_STYLES)}"
        )
    mesh_definitions: tuple[tuple[str, str], ...] = definition["meshes"]
    shadow_mesh: str | None = definition["shadow"]
    controller: dict[str, str] | None = definition["controller"]
    extra_names = {
        name
        for style_definition in FEMALE_HAIR_STYLES.values()
        for name, _ in style_definition["meshes"][1:]
    }
    controller_names = {"Animated1507", "hair_dangle"}

    appearances = document["Data"]["RootChunk"].get("appearances")
    if not isinstance(appearances, list) or not appearances:
        raise ValueError("The app JSON contains no appearances")

    changed: dict[str, dict[str, Any]] = {}
    for appearance in appearances:
        data = appearance["Data"]
        appearance_name = str(_value(data.get("name")))
        components = data.get("components")
        if not isinstance(components, list):
            raise ValueError(f"Appearance {appearance_name} has no components list")

        # Clear additions from a previous retarget while keeping the template's
        # first hair and shadow chunks (their shared binding handles are reused).
        components = [
            component for component in components if _component_name(component) not in extra_names
        ]
        _remove_compiled_components(data, extra_names)
        if controller is None:
            components = [
                component
                for component in components
                if _component_name(component) not in controller_names
            ]
            _remove_compiled_components(data, controller_names)
        data["components"] = components
        by_name = {_component_name(component): component for component in components}
        if "hh_hair" not in by_name or (
            shadow_mesh is not None and "hh_hair_shadow" not in by_name
        ):
            raise ValueError(
                f"Appearance {appearance_name} lacks the clean hair or shadow template components"
            )

        first_name, first_mesh = mesh_definitions[0]
        if first_name != "hh_hair":
            raise ValueError(f"Hairstyle {hairstyle} must define hh_hair as its first mesh")
        for component in _walk_dicts(data):
            if _component_name(component) != "hh_hair" or not isinstance(component.get("mesh"), dict):
                continue
            _set_mesh_value(component, first_mesh)
            if hair_color is not None:
                _set_value(component, "meshAppearance", hair_color)
            component["autoHideDistance"] = 50

        for component_name, mesh_path in mesh_definitions[1:]:
            component = deepcopy(by_name["hh_hair"])
            _set_value(component, "name", component_name)
            _set_mesh_value(component, mesh_path)
            if hair_color is not None:
                _set_value(component, "meshAppearance", hair_color)
            component["id"] = str(_fnv1a64(f"npv_studio:hair:{hairstyle}:{component_name}"))
            components.append(component)

        if shadow_mesh is None:
            components = [
                component
                for component in components
                if _component_name(component) != "hh_hair_shadow"
            ]
            data["components"] = components
            _remove_compiled_components(data, {"hh_hair_shadow"})
        else:
            for component in _walk_dicts(data):
                if _component_name(component) != "hh_hair_shadow" or not isinstance(
                    component.get("mesh"), dict
                ):
                    continue
                _set_mesh_value(component, shadow_mesh)
                _set_value(component, "meshAppearance", "default")
                component["autoHideDistance"] = 21
                component["castLocalShadows"] = "Always"
                component["castShadows"] = "Always"
                component["forceLODLevel"] = -1

        binding_target = "root"
        if controller is not None:
            controller_components = [
                component
                for component in _walk_dicts(data)
                if _component_name(component) in controller_names
                and component.get("$type") == "entAnimatedComponent"
            ]
            if not controller_components:
                raise ValueError(
                    f"Appearance {appearance_name} lacks an animated hair-controller template"
                )
            for component in controller_components:
                _set_value(component, "name", controller["name"])
                component["id"] = str(
                    _fnv1a64(f"npv_studio:hair:{hairstyle}:{controller['name']}")
                )
                _set_resource_value(component, "rig", controller["rig"])
                _set_resource_value(component, "graph", controller["graph"])
            binding_target = controller["name"]

        for component_name, _ in mesh_definitions:
            _rewrite_component_bindings(data, component_name, binding_target)
        if shadow_mesh is not None:
            _rewrite_component_bindings(data, "hh_hair_shadow", "root")
        if controller is not None:
            _rewrite_component_binding_field(data, controller["name"], "parentTransform", "root")

        seamfix_enabled = False
        if require_seamfix:
            seamfixes = [
                component
                for component in components
                if _component_name(component) == "t0_000_pwa_base__full_seamfix"
            ]
            if len(seamfixes) != 1:
                raise ValueError(
                    f"Appearance {appearance_name} must contain exactly one seamfix; "
                    f"found {len(seamfixes)}"
                )
            enabled = seamfixes[0].get("isEnabled")
            if isinstance(enabled, dict) and enabled.get("$value") in (False, 0):
                raise ValueError(f"Appearance {appearance_name} has seamfix disabled")
            seamfix_enabled = True

        changed[appearance_name] = {
            "hair_components": [
                {"name": component_name, "mesh": mesh_path}
                for component_name, mesh_path in mesh_definitions
            ],
            "hair_shadow_mesh": shadow_mesh,
            "binding_target": binding_target,
            "controller": deepcopy(controller),
            "seamfix_component": (
                "t0_000_pwa_base__full_seamfix" if require_seamfix else None
            ),
            "seamfix_enabled": seamfix_enabled,
        }

    return {
        "hairstyle": hairstyle,
        "hair_components": [
            {"name": component_name, "mesh": mesh_path}
            for component_name, mesh_path in mesh_definitions
        ],
        "hair_shadow_mesh": shadow_mesh,
        "controller": deepcopy(controller),
        "changed_by_appearance": changed,
    }


def retarget_female_hair_document(
    document: dict[str, Any], hairstyle: int
) -> dict[str, Any]:
    """Retarget a compiled NPV app when it still has clean hair templates."""
    return _apply_female_hair_style(
        document,
        hairstyle,
        hair_color=None,
        require_seamfix=True,
    )


def apply_female_npc_body_document(
    document: dict[str, Any], *, skin_base: str
) -> dict[str, Any]:
    """Use the vanilla NPC woman body architecture found in the Triad reference.

    The NPC full-body mesh includes its arms, unlike the prepared player-body
    template. Separate player arms and the player seam-fix overlay must be
    removed to avoid overlapping geometry. The mesh exposes naked appearances
    for the six base NPC skin families but not player-only tone variants.
    """

    supported_skin_bases = {
        "01_ca_pale",
        "02_ca_limestone",
        "03_ca_senna",
        "04_ca_almond",
        "05_bl_espresso",
        "06_bl_dark",
    }
    if skin_base not in supported_skin_bases:
        raise ValueError(
            f"NPC woman body does not have a verified {skin_base!r} appearance"
        )

    appearances = document["Data"]["RootChunk"].get("appearances")
    if not isinstance(appearances, list) or not appearances:
        raise ValueError("The app JSON contains no appearances")

    changed: dict[str, dict[str, Any]] = {}
    body_appearance = f"{skin_base}_naked"
    npc_removed_components = FEMALE_NPC_BODY_REMOVED_COMPONENTS | {
        FEMALE_DUAL_BODY_COMPONENTS["nude_large"],
        FEMALE_DUAL_BODY_COMPONENTS["nipples_nude_large"],
    } | FEMALE_GENERATED_TATTOO_COMPONENTS
    for appearance in appearances:
        data = appearance["Data"]
        appearance_name = str(_value(data.get("name")))
        components = data.get("components")
        if not isinstance(components, list):
            raise ValueError(f"Appearance {appearance_name} has no components list")

        removed = [
            str(name)
            for component in components
            if (name := _component_name(component)) in npc_removed_components
        ]
        data["components"] = [
            component
            for component in components
            if _component_name(component) not in npc_removed_components
        ]
        for name in _remove_compiled_components(data, npc_removed_components):
            if name not in removed:
                removed.append(name)

        body_updates = 0
        for component in _walk_dicts(data):
            if _component_name(component) != "t0_body" or not isinstance(
                component.get("mesh"), dict
            ):
                continue
            _set_mesh_value(component, FEMALE_NPC_BODY_MESH)
            _set_value(component, "meshAppearance", body_appearance)
            component["chunkMask"] = "9223372036854775583"
            body_updates += 1
        if body_updates == 0:
            raise ValueError(f"Appearance {appearance_name} has no editable t0_body")

        changed[appearance_name] = {
            "body_mesh": FEMALE_NPC_BODY_MESH,
            "body_appearance": body_appearance,
            "body_skin": body_appearance,
            "body_chunk_mask": "9223372036854775583",
            "seamfix_mesh": None,
            "seamfix_component": None,
            "seamfix_enabled": False,
            "removed_components": sorted(set(removed)),
            "body_component_updates": body_updates,
        }

    return {
        "body_mesh": FEMALE_NPC_BODY_MESH,
        "body_appearance": body_appearance,
        "removed_components": sorted(
            {
                name
                for appearance_changes in changed.values()
                for name in appearance_changes["removed_components"]
            }
        ),
        "changed_by_appearance": changed,
    }


def compile_female_appearance_document(
    document: dict[str, Any], character: CharacterConfig
) -> dict[str, Any]:
    """Apply the supported text-preset appearance fields to a WolvenKit app JSON document."""
    if character.body_frame is not BodyFrame.FEMALE:
        raise ValueError("The appearance compiler currently supports the feminine frame only")

    selection = character.appearance
    skin_base = SKIN_TONES[selection.skin_tone]
    # Named tone variants already contain an underscore-separated qualifier.
    # Their complexion appearances use a double separator (for example,
    # 03_ca_senna_00_amber__d04), while base tones use a single separator.
    separator = "__" if any(f"_{index:02d}_" in skin_base for index in range(3)) else "_"
    skin_suffix = "" if selection.skin_type == 1 else f"{separator}d{selection.skin_type:02d}"
    head_skin = f"{skin_base}{skin_suffix}"
    eye_color = EYE_COLORS.get(selection.eye_color)
    hair_color = HAIR_COLORS.get(selection.hair_color)
    nail_color = NAIL_COLORS.get(selection.nail_color)
    if eye_color is None:
        raise ValueError(f"No verified feminine eye-color mapping for {selection.eye_color}")
    if hair_color is None:
        raise ValueError(f"No verified hair-color mapping for {selection.hair_color}")
    hair_style = FEMALE_HAIR_STYLES.get(selection.hairstyle)
    if hair_style is None:
        raise ValueError(
            f"The first appearance compiler only verifies feminine hairstyles "
            f"{sorted(FEMALE_HAIR_STYLES)}, got {selection.hairstyle}"
        )
    if nail_color is None:
        raise ValueError(f"No verified nail-color mapping for {selection.nail_color}")
    hair_color = hair_color_appearance(
        BodyFrame.FEMALE, selection.hairstyle, selection.hair_color
    )
    selected_chest = selection.chest
    selected_body_mesh = FEMALE_BODY_MESHES[selected_chest]
    body_variants = _female_body_variants(selected_chest)
    alternate_chest = "big" if selected_chest != "big" else "default"
    alternate_body_name = next(
        name for chest, name, _enabled in body_variants if chest == alternate_chest
    )
    alternate_body_mesh = FEMALE_BODY_MESHES[alternate_chest]
    tattoo_meshes = {
        chest: FEMALE_BODY_TATTOOS[
            "big" if chest == "big" else "default"
        ].get(selection.body_tattoos)
        for chest, _name, _enabled in body_variants
    }
    if selection.body_tattoos and any(
        mesh is None for mesh in tattoo_meshes.values()
    ):
        raise ValueError(
            "No exact selected, normal, and big body-tattoo set for "
            f"selection {selection.body_tattoos}"
        )
    selected_tattoo_mesh = tattoo_meshes[selected_chest]
    alternate_tattoo_mesh = tattoo_meshes[alternate_chest]
    nipple_mesh = FEMALE_BIG_NIPPLES.get(selection.nipples)
    if selection.nipples and nipple_mesh is None:
        raise ValueError(f"No verified large-chest nipple mapping for {selection.nipples}")
    body_tattoo_appearance = (
        f"{skin_base}{BODY_TATTOO_APPEARANCE_SUFFIX[selection.body_tattoos]}"
        if selection.body_tattoos
        else None
    )
    nipple_appearance = (
        f"{skin_base}{FEMALE_NIPPLE_APPEARANCE_SUFFIX[selection.nipples]}"
        if selection.nipples
        else None
    )
    tattoo_component_name = _female_tattoo_component_names(selection.body_tattoos)[0]

    root = document["Data"]["RootChunk"]
    appearances = root.get("appearances")
    if not isinstance(appearances, list) or not appearances:
        raise ValueError("The app JSON contains no appearances")

    removed_by_appearance: dict[str, list[str]] = {}
    changed_by_appearance: dict[str, dict[str, Any]] = {}

    for appearance in appearances:
        data = appearance["Data"]
        appearance_name = str(_value(data.get("name")))
        components = data.get("components")
        if not isinstance(components, list):
            raise ValueError(f"Appearance {appearance_name} has no components list")

        head_template = next(
            (
                component
                for preferred in (
                    "he_eyes",
                    "hx_makeup_eyes",
                    "hx_makeup_freckles",
                    "hx_makeup_lips_01",
                    "h0_cyberware_face",
                    "i1_earring",
                )
                for component in components
                if _component_name(component) == preferred
                and isinstance(component.get("mesh"), dict)
            ),
            None,
        )
        if head_template is None and _has_requested_head_visuals(character):
            raise ValueError(
                f"Appearance {appearance_name} has no face-bound component template"
            )

        generated_body_components = {
            FEMALE_DUAL_BODY_COMPONENTS["nude_large"],
            FEMALE_DUAL_BODY_COMPONENTS["clothing_safe_alternate"],
            FEMALE_DUAL_BODY_COMPONENTS["nipples_nude_large"],
            FEMALE_DUAL_BODY_COMPONENTS["nipples_clothing_safe"],
            FEMALE_DUAL_BODY_COMPONENTS["nipples_selected"],
            FEMALE_DUAL_BODY_COMPONENTS["nipples_alternate"],
            "t0_000_pwa_base__full_seamfix",
        } | FEMALE_GENERATED_TATTOO_COMPONENTS | GENERATED_BODY_DETAIL_COMPONENTS | ACM_EMPTY_SLOT_NAMES
        removed: list[str] = []
        kept: list[dict[str, Any]] = []
        for component in components:
            name = _component_name(component)
            should_remove = (
                name in OFF_COMPONENTS
                or name in generated_body_components
                or _is_generated_head_component(name)
            )
            if name == "heb_eyebrows" and selection.eyebrows == 0:
                should_remove = True
            if name in {"Animated1507", "hair_dangle"} and hair_style["controller"] is None:
                should_remove = True
            if should_remove:
                if name not in generated_body_components:
                    removed.append(str(name))
            else:
                kept.append(component)
        for name in _remove_compiled_components(
            data,
            set(OFF_COMPONENTS)
            | generated_body_components
            | ({"heb_eyebrows"} if selection.eyebrows == 0 else set())
            | {
                str(_component_name(component))
                for component in components
                if _is_generated_head_component(_component_name(component))
            },
        ):
            if name in generated_body_components:
                continue
            if name not in removed:
                removed.append(name)
        data["components"] = kept
        by_name = {_component_name(component): component for component in kept}
        starter_outfit = apply_default_starter_outfit(data, character)

        required = {
            "h0_head",
            "he_eyes",
            "ht_teeth",
            "t0_body",
            "an0__arm_right",
            "an0__arm_left",
            "an0_nails_right",
            "an0_nails_left",
            "s0_flat_feet",
            "s0_heeled_feet",
            "hh_hair",
        }
        if selection.eyebrows:
            required.add("heb_eyebrows")
        if hair_style["shadow"] is not None:
            required.add("hh_hair_shadow")
        if hair_style["controller"] is not None:
            required.add("Animated1507")
        missing = sorted(required - by_name.keys())
        if missing:
            raise ValueError(f"Appearance {appearance_name} is missing components: {', '.join(missing)}")

        _set_value(by_name["h0_head"], "meshAppearance", head_skin)
        _set_value(by_name["he_eyes"], "meshAppearance", eye_color)
        _set_value(by_name["ht_teeth"], "meshAppearance", TEETH_APPEARANCES[selection.teeth])
        eyebrow_appearance = (
            f"{HAIR_COLORS[selection.eyebrow_color]}__{selection.eyebrows:02d}"
            if selection.eyebrows
            else None
        )
        if eyebrow_appearance is not None:
            _set_value(by_name["heb_eyebrows"], "meshAppearance", eyebrow_appearance)

        head_visuals = (
            _head_visual_components(head_template, character, skin_base=skin_base)
            if head_template is not None
            else []
        )
        head_anchor_name = str(_component_name(head_template))
        head_index = next(
            index
            for index, component in enumerate(kept)
            if _component_name(component) == head_anchor_name
        )
        kept[head_index + 1 : head_index + 1] = head_visuals
        compiled_head_section = bool(head_visuals) and (
            _insert_compiled_components_after(data, head_anchor_name, head_visuals)
            if _compiled_component_exists(data, head_anchor_name)
            else False
        )
        by_name.update(
            {
                str(_component_name(component)): component
                for component in head_visuals
            }
        )

        for name in ("t0_body", "an0__arm_right", "an0__arm_left", "s0_flat_feet", "s0_heeled_feet"):
            _set_value(by_name[name], "meshAppearance", skin_base)
        normal_enabled = selected_chest == "default"
        _set_mesh_value(by_name["t0_body"], FEMALE_BODY_MESHES["default"])
        _set_component_enabled(by_name["t0_body"], normal_enabled)
        body_variant_components = [
            _body_variant_component(
                by_name["t0_body"],
                name=name,
                mesh=FEMALE_BODY_MESHES[chest],
                appearance=skin_base,
                enabled=enabled,
            )
            for chest, name, enabled in body_variants[1:]
        ]
        body_section_components = list(body_variant_components)
        seamfix = _body_overlay_component(
            by_name["t0_body"],
            name="t0_000_pwa_base__full_seamfix",
            mesh=FEMALE_SEAMFIX,
            appearance=skin_base,
            shadows=False,
        )
        body_section_components.append(seamfix)
        if selected_tattoo_mesh is not None:
            for chest, _body_name, enabled in body_variants:
                suffix = _female_variant_suffix(chest, selected_chest)
                tattoo = _body_overlay_component(
                    by_name["t0_body"],
                    name=f"{tattoo_component_name}{suffix}",
                    mesh=tattoo_meshes[chest],
                    appearance=body_tattoo_appearance,
                    shadows=True,
                )
                _set_component_enabled(tattoo, enabled)
                body_section_components.append(tattoo)
        if nipple_mesh is not None:
            for chest, _body_name, enabled in body_variants:
                suffix = _female_variant_suffix(chest, selected_chest)
                nipple_name = (
                    FEMALE_DUAL_BODY_COMPONENTS["nipples_selected"]
                    if chest == "default"
                    else (
                        FEMALE_DUAL_BODY_COMPONENTS["nipples_nude_large"]
                        if chest == "big"
                        else FEMALE_DUAL_BODY_COMPONENTS["nipples_alternate"]
                    )
                )
                nipples = _body_overlay_component(
                    by_name["t0_body"],
                    name=nipple_name,
                    mesh=female_nipple_depot_path(chest),
                    appearance=nipple_appearance,
                    shadows=False,
                )
                _set_component_enabled(nipples, enabled)
                body_section_components.append(nipples)
        body_details = _body_detail_components(
            by_name["t0_body"], character, skin_base=skin_base
        )
        body_section_components.extend(body_details)
        body_index = next(
            index
            for index, component in enumerate(kept)
            if _component_name(component) == "t0_body"
        )
        kept[body_index + 1 : body_index + 1] = body_section_components
        compiled_body_section = _insert_compiled_components_after(
            data, "t0_body", body_section_components
        )
        acm_slots = (
            _add_empty_acm_slots(data, by_name["t0_body"])
            if character.output.acm_slots
            else []
        )
        female_nails = NAIL_MESHES[BodyFrame.FEMALE][selection.nail_style]
        _set_mesh_value(by_name["an0_nails_right"], female_nails["right"])
        _set_mesh_value(by_name["an0_nails_left"], female_nails["left"])
        _set_value(by_name["an0_nails_right"], "meshAppearance", nail_color)
        _set_value(by_name["an0_nails_left"], "meshAppearance", nail_color)

        removed_by_appearance[appearance_name] = removed
        changed_by_appearance[appearance_name] = {
            "head_skin": head_skin,
            "body_skin": skin_base,
            "eye_color": eye_color,
            "eyebrows": eyebrow_appearance,
            "head_visual_components": [
                {
                    "name": _component_name(component),
                    "mesh": _value(component.get("mesh", {}).get("DepotPath")),
                    "appearance": _value(component.get("meshAppearance")),
                    "chunk_mask": component.get("chunkMask"),
                }
                for component in head_visuals
            ],
            "compiled_head_section": compiled_head_section,
            "hair_color": hair_color,
            "nails": nail_color,
            "nail_style": selection.nail_style,
            "nail_meshes": female_nails,
            "teeth": TEETH_APPEARANCES[selection.teeth],
            "chest": selected_chest,
            "requested_chest": selection.chest,
            "body_mesh": selected_body_mesh,
            "selected_body_mesh": selected_body_mesh,
            "selected_body_enabled": True,
            "alternate_chest": alternate_chest,
            "alternate_body_component": alternate_body_name,
            "alternate_body_mesh": alternate_body_mesh,
            "alternate_body_enabled": False,
            "clothing_safe_body_mesh": FEMALE_BODY_MESHES["default"],
            "nude_large_body_mesh": FEMALE_BODY_MESHES["big"],
            "clothing_safe_body_enabled": normal_enabled,
            "nude_large_body_enabled": selected_chest == "big",
            "compiled_body_section": compiled_body_section,
            "empty_acm_slots": acm_slots,
            "seamfix_mesh": FEMALE_SEAMFIX,
            "body_tattoo_mesh": selected_tattoo_mesh,
            "body_tattoo_appearance": body_tattoo_appearance,
            "selected_tattoo_mesh": selected_tattoo_mesh,
            "alternate_tattoo_mesh": alternate_tattoo_mesh,
            "clothing_safe_tattoo_mesh": FEMALE_BODY_TATTOOS["default"].get(
                selection.body_tattoos
            ),
            "nude_large_tattoo_mesh": FEMALE_BODY_TATTOOS["big"].get(
                selection.body_tattoos
            ),
            "nipple_mesh": female_nipple_depot_path(selected_chest) if nipple_mesh else None,
            "selected_nipple_mesh": (
                female_nipple_depot_path(selected_chest) if nipple_mesh else None
            ),
            "alternate_nipple_mesh": (
                female_nipple_depot_path(alternate_chest) if nipple_mesh else None
            ),
            "nipple_appearance": nipple_appearance,
            "body_variants": [
                {
                    "chest": chest,
                    "component": name,
                    "mesh": FEMALE_BODY_MESHES[chest],
                    "enabled": enabled,
                }
                for chest, name, enabled in body_variants
            ],
            "body_detail_components": [
                {
                    "name": _component_name(component),
                    "mesh": _value(component.get("mesh", {}).get("DepotPath")),
                    "appearance": _value(component.get("meshAppearance")),
                    "chunk_mask": component.get("chunkMask"),
                }
                for component in body_details
            ],
            "starter_outfit": starter_outfit,
        }

    hair_report = _apply_female_hair_style(
        document,
        selection.hairstyle,
        hair_color=hair_color,
        require_seamfix=True,
    )
    for appearance_name, hair_changes in hair_report["changed_by_appearance"].items():
        changed_by_appearance[appearance_name].update(hair_changes)

    return {
        "head_skin": head_skin,
        "body_skin": skin_base,
        "changed_by_appearance": changed_by_appearance,
        "removed_by_appearance": removed_by_appearance,
        "warnings": [
            "Eye-makeup color is absent from valkyrie.txt; compiler default 01 Black was used.",
            "Normal and big feminine torsos are always emitted as stable AMM toggles; "
            "a selected small torso is emitted as a third body option.",
            "When switching torso components, toggle the matching tattoo/nipple overlays; "
            "do not render both torso components simultaneously.",
            "The vanilla feminine seam-fix overlay is enabled in every appearance to cover arm and shoulder gaps.",
            (
                f"Feminine hairstyle {selection.hairstyle:02d} uses its verified native mesh set, "
                "scalp shadow, and static root binding."
                if hair_style["controller"] is None
                else f"Feminine hairstyle {selection.hairstyle:02d} uses its verified native mesh set, "
                "scalp shadow, dangle rig, and animation graph."
            ),
            "Production builds expose one default starter appearance; test-only builds may retain tutorial appearances.",
        ],
    }


def compile_male_appearance_document(
    document: dict[str, Any], character: CharacterConfig
) -> dict[str, Any]:
    """Compile the verified masculine Vincent vertical slice into an app document."""
    if character.body_frame is not BodyFrame.MALE:
        raise ValueError("The masculine appearance compiler requires the masculine frame")

    selection = character.appearance
    skin_base = SKIN_TONES[selection.skin_tone]
    separator = "__" if any(f"_{index:02d}_" in skin_base for index in range(3)) else "_"
    skin_suffix = "" if selection.skin_type == 1 else f"{separator}d{selection.skin_type:02d}"
    head_skin = f"{skin_base}{skin_suffix}"
    eye_color = EYE_COLORS.get(selection.eye_color)
    hair_color = HAIR_COLORS.get(selection.hair_color)
    nail_color = NAIL_COLORS.get(selection.nail_color)
    hair_style = MALE_HAIR_STYLES.get(selection.hairstyle)
    blemish_color = MALE_BLEMISH_COLORS.get(selection.blemish_color)
    if eye_color is None:
        raise ValueError(f"No verified masculine eye-color mapping for {selection.eye_color}")
    if hair_color is None:
        raise ValueError(f"No verified masculine hair-color mapping for {selection.hair_color}")
    if nail_color is None:
        raise ValueError(f"No verified masculine nail-color mapping for {selection.nail_color}")
    if hair_style is None:
        raise ValueError(
            f"No verified masculine hair definition for {selection.hairstyle}; "
            f"supported values are {sorted(MALE_HAIR_STYLES)}"
        )
    hair_color = hair_color_appearance(
        BodyFrame.MALE, selection.hairstyle, selection.hair_color
    )
    if selection.blemishes and blemish_color is None:
        raise ValueError(f"No verified masculine blemish color for {selection.blemish_color}")
    body_tattoo_mesh = MALE_BODY_TATTOOS.get(selection.body_tattoos)
    if selection.body_tattoos and body_tattoo_mesh is None:
        raise ValueError(f"No verified masculine body-tattoo mapping for {selection.body_tattoos}")
    body_tattoo_appearance = (
        f"{skin_base}{BODY_TATTOO_APPEARANCE_SUFFIX[selection.body_tattoos]}"
        if selection.body_tattoos
        else None
    )

    appearances = document["Data"]["RootChunk"].get("appearances")
    if not isinstance(appearances, list) or not appearances:
        raise ValueError("The masculine app JSON contains no appearances")

    removed_by_appearance: dict[str, list[str]] = {}
    changed_by_appearance: dict[str, dict[str, Any]] = {}
    for appearance in appearances:
        data = appearance["Data"]
        appearance_name = str(_value(data.get("name")))
        components = data.get("components")
        if not isinstance(components, list):
            raise ValueError(f"Appearance {appearance_name} has no components list")

        head_template = next(
            (
                component
                for preferred in (
                    "he_eyes",
                    "hx_makeup_eyes",
                    "hx_makeup_freckles",
                    "hx_makeup_lips_01",
                    "h0_cyberware_face",
                    "i1_earring",
                )
                for component in components
                if _component_name(component) == preferred
                and isinstance(component.get("mesh"), dict)
            ),
            None,
        )
        if head_template is None and _has_requested_head_visuals(character):
            raise ValueError(
                f"Appearance {appearance_name} has no face-bound component template"
            )

        generated_male_body_names = {
            f"tx_000_pma_base__full_tattoo_choice_{body_tattoo:02d}"
            for body_tattoo in BODY_TATTOO_MESH_INDEX
        }
        remove_names = {
            "i1_earring",
            "h0x001__personal_slot_decal",
            "i1_004_ma_wrist__silverhand_lace2831",
            "t1_pma_formal__shirt_shadow",
            "heb_eyebrows",
            "t0_peen",
            "t0_pubic_hair",
        } | ACM_EMPTY_SLOT_NAMES | generated_male_body_names | GENERATED_BODY_DETAIL_COMPONENTS | {
            str(_component_name(component))
            for component in components
            if _is_generated_head_component(_component_name(component))
        }
        if selection.eyebrows == 0:
            remove_names.add("heb_eyebrows")
        if selection.beard == 0:
            remove_names.add("hb_beard")
        removed = [
            str(name)
            for component in components
            if (name := _component_name(component)) in remove_names
        ]
        kept = [component for component in components if _component_name(component) not in remove_names]
        data["components"] = kept
        for name in _remove_compiled_components(data, remove_names):
            if name not in removed:
                removed.append(name)
        by_name = {_component_name(component): component for component in kept}
        starter_outfit = apply_default_starter_outfit(data, character)

        required = {
            "h0_head",
            "he_eyes",
            "ht_teeth",
            "a0_nails_l",
            "a0_nails_r",
            "a0_arms_l",
            "a0_arms_r",
            "t0_body",
            "hh_045_pma__short_spiked_cyberware_01",
        }
        if hair_style["shadow"] is not None:
            required.add("hh_045_ma__short_spiked_shadow")
        missing = sorted(required - by_name.keys())
        if missing:
            raise ValueError(f"Appearance {appearance_name} is missing components: {', '.join(missing)}")

        _set_value(by_name["h0_head"], "meshAppearance", head_skin)
        _set_value(by_name["he_eyes"], "meshAppearance", eye_color)
        _set_value(by_name["ht_teeth"], "meshAppearance", TEETH_APPEARANCES[selection.teeth])
        for name in ("t0_body", "a0_arms_l", "a0_arms_r"):
            _set_value(by_name[name], "meshAppearance", skin_base)

        male_body_visuals: list[dict[str, Any]] = []
        if body_tattoo_mesh is not None:
            body_tattoo = _body_overlay_component(
                by_name["t0_body"],
                name=f"tx_000_pma_base__full_tattoo_choice_{selection.body_tattoos:02d}",
                mesh=body_tattoo_mesh,
                appearance=body_tattoo_appearance,
                shadows=True,
            )
            _set_component_enabled(body_tattoo, True)
            male_body_visuals.append(body_tattoo)
        body_details = _body_detail_components(
            by_name["t0_body"], character, skin_base=skin_base
        )
        male_body_visuals.extend(body_details)
        if male_body_visuals:
            body_index = next(
                index
                for index, component in enumerate(kept)
                if _component_name(component) == "t0_body"
            )
            kept[body_index + 1 : body_index + 1] = male_body_visuals
            _insert_compiled_components_after(data, "t0_body", male_body_visuals)

        head_visuals = (
            _head_visual_components(head_template, character, skin_base=skin_base)
            if head_template is not None
            else []
        )
        head_anchor_name = str(_component_name(head_template))
        head_index = next(
            index
            for index, component in enumerate(kept)
            if _component_name(component) == head_anchor_name
        )
        kept[head_index + 1 : head_index + 1] = head_visuals
        compiled_head_section = bool(head_visuals) and (
            _insert_compiled_components_after(data, head_anchor_name, head_visuals)
            if _compiled_component_exists(data, head_anchor_name)
            else False
        )
        by_name.update(
            {
                str(_component_name(component)): component
                for component in head_visuals
            }
        )
        male_nails = NAIL_MESHES[BodyFrame.MALE][selection.nail_style]
        _set_mesh_value(by_name["a0_nails_l"], male_nails["left"])
        _set_mesh_value(by_name["a0_nails_r"], male_nails["right"])
        for name in ("a0_nails_l", "a0_nails_r"):
            _set_value(by_name[name], "meshAppearance", nail_color)

        acm_slots = (
            _add_empty_acm_slots(data, by_name["t0_body"])
            if character.output.acm_slots
            else []
        )

        hair_component_name = "hh_045_pma__short_spiked_cyberware_01"
        hair_shadow_name = "hh_045_ma__short_spiked_shadow"
        mesh_definitions: tuple[tuple[str, str], ...] = hair_style["meshes"]
        hair_component = by_name[hair_component_name]
        _set_mesh_value(hair_component, mesh_definitions[0][1])
        _set_value(hair_component, "meshAppearance", hair_color)
        _set_component_enabled(hair_component, True)
        hair_index = kept.index(hair_component)
        extra_hair_components: list[dict[str, Any]] = []
        for component_name, mesh_path in mesh_definitions[1:]:
            extra = deepcopy(hair_component)
            _set_value(extra, "name", component_name)
            _set_mesh_value(extra, mesh_path)
            _set_value(extra, "meshAppearance", hair_color)
            extra["id"] = str(
                _fnv1a64(f"npv_studio:male_hair:{selection.hairstyle}:{component_name}")
            )
            extra_hair_components.append(extra)
        kept[hair_index + 1 : hair_index + 1] = extra_hair_components
        if extra_hair_components:
            _insert_compiled_components_after(data, hair_component_name, extra_hair_components)

        if hair_style["shadow"] is None:
            kept[:] = [
                component
                for component in kept
                if _component_name(component) != hair_shadow_name
            ]
            _remove_compiled_components(data, {hair_shadow_name})
        else:
            hair_shadow = by_name[hair_shadow_name]
            _set_mesh_value(hair_shadow, hair_style["shadow"])
            _set_component_enabled(hair_shadow, True)

        controller = hair_style["controller"]
        binding_target = "root"
        if controller is not None:
            controller_source = next(
                (
                    component
                    for component in kept
                    if component.get("$type") == "entAnimatedComponent"
                    and _component_name(component) == "face_rig"
                ),
                None,
            )
            if controller_source is None:
                raise ValueError(
                    f"Appearance {appearance_name} has no animated component to seed hair motion"
                )
            hair_controller = deepcopy(controller_source)
            _set_value(hair_controller, "name", controller["name"])
            hair_controller["id"] = str(
                _fnv1a64(f"npv_studio:male_hair:{selection.hairstyle}:controller")
            )
            _set_resource_value(hair_controller, "rig", controller["rig"])
            _set_resource_value(hair_controller, "graph", controller["graph"])
            facial_setup = hair_controller.get("facialSetup")
            if isinstance(facial_setup, dict):
                depot = facial_setup.get("DepotPath")
                if isinstance(depot, dict):
                    depot["$storage"] = "uint64"
                    depot["$value"] = "0"
                facial_setup["Flags"] = "Soft"
            kept.insert(hair_index, hair_controller)
            _insert_compiled_components_after(data, hair_component_name, [hair_controller])
            binding_target = controller["name"]

        _rewrite_component_bindings(data, hair_component_name, binding_target)
        for component_name, _ in mesh_definitions[1:]:
            _rewrite_component_bindings(data, component_name, binding_target)
        if hair_style["shadow"] is not None:
            _rewrite_component_bindings(data, hair_shadow_name, "root")
        if controller is not None:
            _rewrite_component_binding_field(
                data, controller["name"], "parentTransform", "root"
            )

        removed_by_appearance[appearance_name] = removed
        changed_by_appearance[appearance_name] = {
            "head_skin": head_skin,
            "body_skin": skin_base,
            "eye_color": eye_color,
            "eyebrows": "off" if selection.eyebrows == 0 else selection.eyebrows,
            "head_visual_components": [
                {
                    "name": _component_name(component),
                    "mesh": _value(component.get("mesh", {}).get("DepotPath")),
                    "appearance": _value(component.get("meshAppearance")),
                    "chunk_mask": component.get("chunkMask"),
                }
                for component in head_visuals
            ],
            "compiled_head_section": compiled_head_section,
            "body_visual_components": [
                {
                    "name": _component_name(component),
                    "mesh": _value(component.get("mesh", {}).get("DepotPath")),
                    "appearance": _value(component.get("meshAppearance")),
                }
                for component in male_body_visuals
            ],
            "body_tattoo_mesh": body_tattoo_mesh,
            "body_tattoo_appearance": body_tattoo_appearance,
            "hair_mesh": mesh_definitions[0][1],
            "hair_components": [
                {"name": name, "mesh": mesh}
                for name, mesh in mesh_definitions
            ],
            "hair_shadow": hair_style["shadow"],
            "hair_controller": deepcopy(controller),
            "hair_color": hair_color,
            "nails": nail_color,
            "nail_style": selection.nail_style,
            "nail_meshes": male_nails,
            "teeth": TEETH_APPEARANCES[selection.teeth],
            "empty_acm_slots": acm_slots,
            "starter_outfit": starter_outfit,
        }

    return {
        "head_skin": head_skin,
        "body_skin": skin_base,
        "changed_by_appearance": changed_by_appearance,
        "removed_by_appearance": removed_by_appearance,
        "warnings": [
            "The masculine tutorial does not contain an eyelash component; eyelash color 06 is preserved but not rendered.",
            "Selected penis and matching pubic-hair components are compiled but disabled on spawn for manual AMM activation.",
            "Production builds expose one default starter appearance; test-only builds may retain tutorial appearances.",
        ],
    }
