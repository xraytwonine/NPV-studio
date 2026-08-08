from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BodyFrame(StrEnum):
    FEMALE = "female"
    MALE = "male"


class VoiceTone(StrEnum):
    FEMININE = "feminine"
    MASCULINE = "masculine"


class BuildMode(StrEnum):
    DRY_RUN = "dry_run"
    FINAL = "final"


class DependencyKind(StrEnum):
    BUILD = "build"
    RUNTIME_MOD = "runtime_mod"
    OPTIONAL = "optional"


class HeadShape(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eyes: int = Field(default=1, ge=1, le=22)
    nose: int = Field(default=1, ge=1, le=22)
    mouth: int = Field(default=1, ge=1, le=22)
    jaw: int = Field(default=1, ge=1, le=22)
    ears: int = Field(default=1, ge=1, le=22)


class AppearanceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skin_tone: int = Field(default=1, ge=1, le=12)
    skin_type: int = Field(default=1, ge=1, le=5)
    hairstyle: int = Field(default=1, ge=1, le=50)
    hair_color: int = Field(default=1, ge=1, le=35)
    eye_color: int = Field(default=1, ge=1, le=39)
    eyebrows: int = Field(default=1, ge=0, le=11)
    eyebrow_color: int = Field(default=1, ge=1, le=35)
    eyelash_color: int = Field(default=1, ge=1, le=35)
    beard: int = Field(default=0, ge=0, le=12)
    beard_style: int = Field(default=1, ge=1, le=7)
    beard_color: int = Field(default=1, ge=1, le=35)
    cyberware: int = Field(default=0, ge=0, le=8)
    facial_scars: int = Field(default=0, ge=0, le=9)
    facial_tattoos: int = Field(default=0, ge=0, le=11)
    piercings: int = Field(default=0, ge=0, le=16)
    piercing_color: int = Field(default=1, ge=1, le=16)
    teeth: int = Field(default=0, ge=0, le=4)
    eye_makeup: int = Field(default=0, ge=0, le=20)
    eye_makeup_color: int = Field(default=1, ge=1, le=14)
    lip_makeup: int = Field(default=0, ge=0, le=20)
    lip_makeup_color: int = Field(default=1, ge=1, le=14)
    lip_makeup_finish: Literal["off", "default", "glossy", "matte"] = "default"
    cheek_makeup: int = Field(default=0, ge=0, le=14)
    cheek_makeup_color: int = Field(default=1, ge=1, le=8)
    blemishes: int = Field(default=0, ge=0, le=3)
    blemish_color: int = Field(default=1, ge=1, le=6)
    body_tattoos: int = Field(default=0, ge=0, le=7)
    body_scars: int = Field(default=0, ge=0, le=4)
    nipples: int = Field(default=0, ge=0, le=3)
    nail_style: Literal["short", "long"] = "short"
    # Selection 11 is the first material verified end-to-end for both frames.
    nail_color: int = Field(default=11, ge=1, le=37)
    chest: Literal["default", "small", "big"] = "default"
    genitals: Literal["none", "vagina", "penis_1", "penis_2"] = "none"
    penis_size: Literal["unavailable", "small", "default", "big"] = "unavailable"
    pubic_hair_style: int = Field(default=0, ge=0, le=5)
    pubic_hair_color: int = Field(default=1, ge=1, le=5)


class OutputOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_body: bool = True
    starter_outfit: bool = True
    acm_slots: bool = True
    appearance_name: str = "starter_outfit"
    base_body_appearance_name: str = "base_body"
    mode: BuildMode = BuildMode.DRY_RUN
    package_target: Literal["vortex_zip"] = "vortex_zip"

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_base_body_output(cls, value: Any) -> Any:
        if isinstance(value, dict) and "starter_outfit" not in value:
            migrated = dict(value)
            if migrated.get("appearance_name") == "base_body":
                migrated["starter_outfit"] = False
            return migrated
        return value

    @field_validator("appearance_name", "base_body_appearance_name")
    @classmethod
    def validate_appearance_name(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized or not normalized.replace("_", "").isalnum():
            raise ValueError("appearance_name must contain letters, numbers, or underscores")
        return normalized

    @model_validator(mode="after")
    def require_an_appearance(self) -> "OutputOptions":
        if not self.base_body and not self.starter_outfit:
            raise ValueError("At least one of base_body or starter_outfit must be enabled")
        if self.base_body and self.starter_outfit:
            if self.appearance_name == self.base_body_appearance_name:
                raise ValueError("Starter outfit and base body appearance names must be unique")
        return self


class CharacterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    game_version: str = "2.3"
    name: str = "My V"
    namespace: str = "my_v"
    body_frame: BodyFrame = BodyFrame.FEMALE
    voice: VoiceTone = VoiceTone.FEMININE
    head: HeadShape = Field(default_factory=HeadShape)
    appearance: AppearanceSelection = Field(default_factory=AppearanceSelection)
    output: OutputOptions = Field(default_factory=OutputOptions)

    @model_validator(mode="after")
    def validate_frame_dependent_selections(self) -> "CharacterConfig":
        if self.body_frame is BodyFrame.MALE and self.appearance.chest != "default":
            raise ValueError("Chest selection must be default for the masculine base frame")
        if self.body_frame is BodyFrame.FEMALE and self.appearance.piercings > 14:
            raise ValueError("Piercing selections 15 and 16 are available only for the masculine frame")
        if not self.appearance.genitals.startswith("penis") and self.appearance.penis_size != "unavailable":
            raise ValueError("Penis size is available only when a penis genital option is selected")
        return self

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Character name cannot be empty")
        return value[:80]

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        if not normalized or not normalized.replace("_", "").isalnum():
            raise ValueError("Namespace must contain letters, numbers, or underscores")
        if not normalized[0].isalpha():
            normalized = f"npv_{normalized}"
        return normalized[:64]


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    game_root: Path
    workspace_root: Path
    blender_executable: Path | None = None
    blender_addon_root: Path | None = None
    wolvenkit_gui_executable: Path | None = None
    wolvenkit_executable: Path | None = None
    npv_template_root: Path | None = None
    character_source_path: Path | None = None
    preset_root: Path | None = None
    package_output_root: Path | None = None
    allow_external_tools: bool = False
    install_enabled: Literal[False] = False

    @model_validator(mode="after")
    def enforce_read_only_game_root(self) -> "AppSettings":
        game = self.game_root.resolve(strict=False)
        workspace = self.workspace_root.resolve(strict=False)
        if game == workspace or game in workspace.parents or workspace in game.parents:
            raise ValueError("workspace_root and game_root must be completely separate")
        for label, configured in (
            ("preset_root", self.preset_root),
            ("package_output_root", self.package_output_root),
        ):
            if configured is None:
                continue
            resolved = configured.resolve(strict=False)
            if resolved == game or resolved in game.parents or game in resolved.parents:
                raise ValueError(f"{label} must not overlap the read-only game root")
        return self


class DependencyStatus(BaseModel):
    name: str
    available: bool
    path: Path | None = None
    kind: DependencyKind = DependencyKind.BUILD
    required_for_dry_run: bool = False
    details: str = ""


class ComponentSlot(BaseModel):
    category: str
    component_name: str
    prefix: str
    initially_visible: bool = False
    placeholder_strategy: str = "validated_hidden_template_component"


class StarterGarment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: Literal["inner_torso", "legs", "feet"]
    component_name: str
    display_name: str
    item_id: str
    mesh_path: str
    mesh_appearance: str | None = None
    chunk_mask: str | None = None

    @field_validator("mesh_path")
    @classmethod
    def validate_mesh_path(cls, value: str) -> str:
        normalized = value.strip().replace("/", "\\")
        if not normalized.startswith("base\\") or not normalized.endswith(".mesh"):
            raise ValueError("Starter garment mesh_path must be a base\\...\\*.mesh resource")
        if ".." in normalized.split("\\"):
            raise ValueError("Starter garment mesh_path may not contain traversal")
        return normalized


class BuildReport(BaseModel):
    schema_version: Literal[1] = 1
    build_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: BuildMode = BuildMode.DRY_RUN
    output_root: Path
    character: CharacterConfig
    dependencies: list[DependencyStatus]
    component_slots: list[ComponentSlot]
    generated_files: list[Path]
    warnings: list[str]
    success: bool

    def as_json_data(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
