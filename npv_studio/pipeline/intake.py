from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from npv_studio.domain.models import BodyFrame, CharacterConfig, VoiceTone


ALIASES = {
    "skintone": "appearance.skin_tone",
    "skintype": "appearance.skin_type",
    "skin": "appearance.skin_type",
    "custom hair": "appearance.hairstyle",
    "hairstyle": "appearance.hairstyle",
    "haircolor": "appearance.hair_color",
    "hair color": "appearance.hair_color",
    "eyes": "head.eyes",
    "eye color": "appearance.eye_color",
    "eyebrows": "appearance.eyebrows",
    "eyebrow colr": "appearance.eyebrow_color",
    "eyebrow color": "appearance.eyebrow_color",
    "eyelesh colr": "appearance.eyelash_color",
    "eyelash color": "appearance.eyelash_color",
    "nose": "head.nose",
    "mouth": "head.mouth",
    "jaw": "head.jaw",
    "ears": "head.ears",
    "beard": "appearance.beard",
    "beard style": "appearance.beard_style",
    "beard color": "appearance.beard_color",
    "cyberware": "appearance.cyberware",
    "facial scars": "appearance.facial_scars",
    "facial tatt": "appearance.facial_tattoos",
    "face tatt": "appearance.facial_tattoos",
    "piercings": "appearance.piercings",
    "piercing color": "appearance.piercing_color",
    "teeth": "appearance.teeth",
    "eye makeup": "appearance.eye_makeup",
    "eye makeup color": "appearance.eye_makeup_color",
    "lip mkup st": "appearance.lip_makeup",
    "lip makeup": "appearance.lip_makeup",
    "lip makeup color": "appearance.lip_makeup_color",
    "lip makeup style": "appearance.lip_makeup_finish",
    "cheek mkup": "appearance.cheek_makeup",
    "cheek makeup": "appearance.cheek_makeup",
    "cheek makeup color": "appearance.cheek_makeup_color",
    "cheek mkup color": "appearance.cheek_makeup_color",
    "blemishes": "appearance.blemishes",
    "blemishcolor": "appearance.blemish_color",
    "nails": "appearance.nail_style",
    "nail color": "appearance.nail_color",
    "body tat": "appearance.body_tattoos",
    "body tatts": "appearance.body_tattoos",
    "breast": "appearance.chest",
    "breast big": "appearance.chest",
    "nipples": "appearance.nipples",
    "body scars": "appearance.body_scars",
    "genitals": "appearance.genitals",
    "pubic hair": "appearance.pubic_hair_style",
    "pubic color": "appearance.pubic_hair_color",
    "penis": "appearance.genitals",
    "penis size": "appearance.penis_size",
    "pubic hair style": "appearance.pubic_hair_style",
    "pubic hair color": "appearance.pubic_hair_color",
    "public hair style": "appearance.pubic_hair_style",
    "public hair color": "appearance.pubic_hair_color",
}


def _normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _coerce(value: str) -> int | str:
    cleaned = " ".join(value.split())
    return int(cleaned) if re.fullmatch(r"-?\d+", cleaned) else cleaned


def _normalize_mapped_value(target: str, value: int | str) -> int | str:
    normalized = str(value).strip().lower()
    numeric_targets = {
        "appearance.eyebrows",
        "appearance.beard",
        "appearance.beard_style",
        "appearance.beard_color",
        "appearance.cyberware",
        "appearance.facial_scars",
        "appearance.facial_tattoos",
        "appearance.piercings",
        "appearance.piercing_color",
        "appearance.eye_makeup",
        "appearance.lip_makeup",
        "appearance.cheek_makeup",
        "appearance.cheek_makeup_color",
        "appearance.blemishes",
        "appearance.body_tattoos",
        "appearance.nipples",
        "appearance.pubic_hair_style",
        "appearance.pubic_hair_color",
    }
    if target in numeric_targets:
        if normalized in {"off", "none", "0/off"}:
            return 0
        if normalized in {"on", "yes"}:
            return 1
        leading_number = re.match(r"^(\d+)(?:\D.*)?$", normalized)
        if leading_number:
            return int(leading_number.group(1))
    if target == "appearance.nail_style":
        if normalized in {"0", "1", "01", "short"}:
            return "short"
        if normalized in {"2", "02", "long"}:
            return "long"
    if target == "appearance.chest":
        for choice in ("default", "small", "big"):
            if choice in normalized.split():
                return choice
    if target == "appearance.lip_makeup_finish":
        for finish in ("off", "default", "glossy", "matte"):
            if finish in normalized:
                return finish
    if target == "appearance.genitals":
        if normalized in {"0", "off", "none"}:
            return "none"
        if "vagina" in normalized:
            return "vagina"
        match = re.search(r"(?:penis\s*)?([12])", normalized)
        if match:
            return f"penis_{match.group(1)}"
    if target == "appearance.penis_size":
        for size in ("unavailable", "small", "default", "big"):
            if size in normalized:
                return size
    return value


def analyze_character_source(path: Path) -> dict[str, Any]:
    source = path.resolve(strict=True)
    mapped: dict[str, int | str] = {}
    occurrences: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown: list[dict[str, Any]] = []
    metadata: dict[str, str] = {}

    for line_number, raw_line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^(.*?)(?:\t+|\s{2,})(\S.*)$", raw_line)
        if not match:
            normalized_line = _normalize_label(line)
            if line_number == 1:
                metadata["display_name"] = line
                continue
            if normalized_line in {"masc", "male", "masculine"}:
                metadata["body_frame"] = BodyFrame.MALE.value
                metadata["voice"] = VoiceTone.MASCULINE.value
                continue
            if normalized_line in {"fem", "female", "feminine"}:
                metadata["body_frame"] = BodyFrame.FEMALE.value
                metadata["voice"] = VoiceTone.FEMININE.value
                continue
            unknown.append({"line": line_number, "text": line, "reason": "Could not split label and value"})
            continue
        label, raw_value = match.groups()
        normalized = _normalize_label(label)
        target = ALIASES.get(normalized)
        if target is None:
            unknown.append({"line": line_number, "text": line, "reason": "Unknown label"})
            continue
        value = _normalize_mapped_value(target, _coerce(raw_value))
        occurrences[target].append({"line": line_number, "label": label.strip(), "value": value})

    duplicates: list[dict[str, Any]] = []
    for target, entries in occurrences.items():
        if len(entries) == 1:
            mapped[target] = entries[0]["value"]
        else:
            duplicates.append({"target": target, "entries": entries})

    unmodeled = {key: value for key, value in mapped.items() if key.startswith("unmodeled.")}
    supported = {key: value for key, value in mapped.items() if not key.startswith("unmodeled.")}
    return {
        "schema_version": 1,
        "source": str(source),
        "metadata": metadata,
        "supported_values": supported,
        "recognized_but_not_yet_modeled": unmodeled,
        "ambiguous_duplicates": duplicates,
        "unknown_lines": unknown,
        "safe_to_generate_supported_draft": not duplicates and not unknown,
        "ready_for_full_fidelity_preset": not duplicates and not unknown and not unmodeled,
        "notes": [
            "No game files were read or changed.",
            "Ambiguous duplicate fields are intentionally omitted instead of guessed.",
            "Recognized unmodeled fields are preserved for the expanded character schema.",
        ],
    }


def character_draft_from_source(
    path: Path,
    *,
    name: str,
    namespace: str,
    body_frame: BodyFrame | None = None,
    voice: VoiceTone | None = None,
) -> CharacterConfig:
    result = analyze_character_source(path)
    if not result["safe_to_generate_supported_draft"]:
        raise ValueError("Character source contains ambiguous or unknown fields")
    head: dict[str, Any] = {}
    appearance: dict[str, Any] = {}
    for target, value in result["supported_values"].items():
        section, key = target.split(".", 1)
        if section == "head":
            head[key] = value
        elif section == "appearance":
            appearance[key] = value
    detected_frame = BodyFrame(result["metadata"].get("body_frame", BodyFrame.FEMALE.value))
    resolved_frame = body_frame or detected_frame
    detected_voice = VoiceTone(
        result["metadata"].get(
            "voice",
            VoiceTone.MASCULINE.value if resolved_frame is BodyFrame.MALE else VoiceTone.FEMININE.value,
        )
    )
    return CharacterConfig(
        name=name,
        namespace=namespace,
        body_frame=resolved_frame,
        voice=voice or detected_voice,
        head=head,
        appearance=appearance,
    )


def load_character_config(
    path: Path,
    *,
    name: str | None = None,
    namespace: str | None = None,
) -> CharacterConfig:
    """Load either an NPV Studio JSON preset or a creator-value text file."""
    source = Path(path).resolve(strict=True)
    if source.suffix.casefold() == ".json":
        character = CharacterConfig.model_validate_json(source.read_text(encoding="utf-8-sig"))
        updates: dict[str, str] = {}
        if name:
            updates["name"] = name
        if namespace:
            updates["namespace"] = namespace
        return character.model_copy(update=updates) if updates else character

    analysis = analyze_character_source(source)
    display_name = name or analysis["metadata"].get("display_name") or source.stem
    generated_namespace = re.sub(r"[^a-z0-9_]+", "_", display_name.casefold()).strip("_")
    return character_draft_from_source(
        source,
        name=display_name,
        namespace=namespace or generated_namespace or "my_v",
    )
