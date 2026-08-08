from __future__ import annotations

from npv_studio.domain.models import BodyFrame


CYBERWARE = {
    1: {"mesh": "cyberware_01", "female": "cyberware_01", "male": "cyberware_01__dark", "chunk_mask": None},
    2: {"mesh": "cyberware_02", "female": "cyberware_02", "male": "cyberware_02__dark", "chunk_mask": None},
    3: {"mesh": "makeup_freckles_01", "female": "cyberware_04", "male": "cyberware_04", "chunk_mask": None},
    4: {"mesh": "cyberware_04", "female": "cyberware_04", "male": "cyberware_04__dark", "chunk_mask": None},
    5: {"mesh": "makeup_freckles_01", "female": "cyberware_06", "male": "cyberware_06", "chunk_mask": None},
    6: {"mesh": "cyberware_06", "female": "cyberware_06", "male": "cyberware_06__dark", "chunk_mask": 1},
    7: {"mesh": "cyberware_07", "female": "cyberware_07", "male": "cyberware_07__dark", "chunk_mask": None},
    8: {"mesh": "makeup_eyes_01", "female": "cyberware_01", "male": "cyberware_01", "chunk_mask": None},
}

FACIAL_SCAR_CHUNK_MASKS = {1: 1, 2: 2, 3: 4, 4: 16, 5: 32, 6: 64, 7: 128, 8: 256, 9: 1024}

# Creator selections 1-6 use tattoo meshes 06-10 (5 and 6 are different
# submeshes of tattoo 10); selections 7-11 use meshes 01-05.
FACIAL_TATTOO_MESHES = {
    1: "tattoo_06", 2: "tattoo_07", 3: "tattoo_08", 4: "tattoo_09",
    5: "tattoo_10", 6: "tattoo_10", 7: "tattoo_01", 8: "tattoo_02",
    9: "tattoo_03", 10: "tattoo_04", 11: "tattoo_05",
}

# Creator choices 05 and 06 deliberately share tattoo_10 geometry.  Choice 05
# is the second submesh/material family from hx_000__tattoo_11.app: bit zero is
# hidden and every skin appearance has the trailing underscore variant.  These
# values are part of the output identity; omitting them aliases choice 06 to 05.
FACIAL_TATTOO_CHUNK_MASKS = {
    selection: (18446744073709551614 if selection == 5 else 9223372036854775807)
    for selection in FACIAL_TATTOO_MESHES
}
FACIAL_TATTOO_APPEARANCE_SUFFIXES = {
    selection: ("_" if selection == 5 else "")
    for selection in FACIAL_TATTOO_MESHES
}

PIERCING_COLORS = {
    1: "silver", 2: "gold", 3: "pearl", 4: "cooper", 5: "plastic_red",
    6: "plastic_pink", 7: "plastic_black", 8: "blue", 9: "mixed",
    10: "mixed2", 11: "neon_teal", 12: "pink_metalic", 13: "rainbow",
    14: "rose_gold", 15: "steel", 16: "wood",
}

_COMMON_PIERCINGS = {
    1: ((1, 4), (2, 1024), (3, 2)),
    2: ((1, 15), (2, 2048)),
    3: ((1, 520), (2, 7200)),
    4: ((1, 4), (2, 2268), (3, 1)),
    5: ((1, 536), (2, 2873), (3, 2)),
    6: ((2, 5153),),
    7: ((1, 514), (2, 2), (3, 2)),
    8: ((1, 520), (2, 8064), (3, 1)),
    9: ((1, 4), (2, 4131)),
    10: ((1, 1548), (2, 6143), (3, 3)),
    11: ((1, 2047),),
}

PIERCINGS = {
    BodyFrame.FEMALE: {
        **_COMMON_PIERCINGS,
        12: ((4, 4),), 13: ((4, 1),), 14: ((4, 2),),
    },
    BodyFrame.MALE: {
        **_COMMON_PIERCINGS,
        12: ((1, 512),), 13: ((1, 8),), 14: ((4, 4),),
        15: ((4, 1),), 16: ((4, 2),),
    },
}

BEARD_MESHES = {
    1: ("shadowbase_01",),
    2: ("shadowbase_01", "big_beard_afro"),
    3: ("shadowbase_01", "default"),
    4: ("shadowbase_01", "handlebar_stache"),
    5: ("shadowbase_01", "jesse_beard"),
    6: ("shadowbase_01", "maelstrom_full"),
    7: ("shadowbase_01", "big_beard"),
    8: ("shadowbase_01", "short_afro"),
    9: ("shadowbase_01", "thick_beard_afro"),
    10: ("shadowbase_01", "fu_manchu"),
    11: ("shadowbase_01", "logan"),
    12: ("shadowbase_01", "patmc"),
}

# The creator's Beard Style control selects an enabled-submesh mask on the
# second beard component.  Shapes 01 and 04 have one fixed outcome; the other
# shapes expose either three or seven exact masks.
_UINT64_MAX = (1 << 64) - 1
_FULL_CHUNK_MASK = (1 << 63) - 1


def _beard_chunk_masks(all_chunks: int, active_masks: tuple[int, ...]) -> dict[int, int]:
    """Translate creator-visible active chunks to the exact CR2W masks.

    Vanilla beard apps encode a full mesh with signed-int64 max.  Partial
    variants are serialized as uint64 masks with the inactive low bits
    cleared.  Keeping this conversion here makes the resource evidence
    reviewable and avoids substituting small logical masks in the entity.
    """
    return {
        index: (
            _FULL_CHUNK_MASK
            if active == all_chunks
            else _UINT64_MAX - (all_chunks ^ active)
        )
        for index, active in enumerate(active_masks, 1)
    }


BEARD_STYLE_CHUNK_MASKS = {
    1: _beard_chunk_masks(1, (1,)),
    2: _beard_chunk_masks(3, (3, 2, 1)),
    3: _beard_chunk_masks(7, (7, 1, 5, 3, 4, 6, 2)),
    4: _beard_chunk_masks(1, (1,)),
    5: _beard_chunk_masks(3, (3, 2, 1)),
    6: _beard_chunk_masks(31, (31, 22, 23, 30, 1, 9, 8)),
    7: _beard_chunk_masks(3, (3, 2, 1)),
    8: _beard_chunk_masks(3, (3, 2, 1)),
    9: _beard_chunk_masks(7, (7, 4, 5, 6, 1, 3, 2)),
    10: _beard_chunk_masks(15, (15, 3, 7, 11, 4, 12, 8)),
    11: _beard_chunk_masks(15, (15, 6, 7, 14, 1, 9, 8)),
    12: _beard_chunk_masks(15, (15, 6, 7, 14, 1, 9, 8)),
}

BEARD_SHADOW_APPEARANCES = {
    1: "beard_shadow_01",
    2: "beard_shadow_02",
    3: "beard_shadow_02",
    4: "beard_shadow_01",
    5: "beard_shadow_02",
    6: "beard_shadow_01",
    7: "beard_shadow_02",
    8: "beard_shadow_02",
    9: "beard_shadow_02",
    10: "beard_shadow_01",
    11: "beard_shadow_01",
    12: "beard_shadow_01",
}


def frame_code(frame: BodyFrame) -> str:
    return "pwa" if frame is BodyFrame.FEMALE else "pma"


def head_mesh_pair(frame: BodyFrame, stem: str) -> tuple[str, str]:
    code = frame_code(frame)
    return f"hx_000_{code}_c__basehead_{stem}", f"hx_000_{code}__morphs_{stem}"


def earring_mesh_pair(frame: BodyFrame, number: int) -> tuple[str, str]:
    code = frame_code(frame)
    return f"i1_000_{code}_c__basehead_earring_{number:02d}", f"i1_000_{code}__morphs_earring_{number:02d}"
