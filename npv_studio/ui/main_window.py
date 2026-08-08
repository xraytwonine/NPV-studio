from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from npv_studio.core.paths import PathGuard
from npv_studio.core.settings import DEFAULT_SETTINGS_PATH, save_settings
from npv_studio.data.loader import load_game_data, selector_range
from npv_studio.domain.models import (
    AppSettings,
    AppearanceSelection,
    BodyFrame,
    CharacterConfig,
    DependencyKind,
    HeadShape,
    OutputOptions,
    VoiceTone,
)
from npv_studio.pipeline.dependencies import DependencyInspector
from npv_studio.pipeline.creator_assets import BEARD_STYLE_CHUNK_MASKS
from npv_studio.pipeline.final_build import FinalBuildBuilder
from npv_studio.pipeline.intake import load_character_config


CYBERPUNK_STYLE = """
QMainWindow, QWidget { background: #101114; color: #e6e8ea; }
QFrame#dependencyContainer { background: #151c20; border: 2px solid #f2d84b; border-radius: 4px; }
QGroupBox { border: 1px solid #3c444c; margin-top: 12px; padding: 12px; font-weight: 600; }
QGroupBox::title { color: #f2d84b; subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QLineEdit, QSpinBox, QComboBox, QTextEdit, QTableWidget {
    background: #181b20; border: 1px solid #4d5863; border-radius: 3px; padding: 5px;
}
QSpinBox:disabled, QComboBox:disabled { color: #ff5c68; border-color: #a52a36; }
QLabel:disabled { color: #ff5c68; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #1bd9cf; }
QPushButton { background: #24313a; border: 1px solid #1bd9cf; border-radius: 3px; padding: 8px 14px; }
QPushButton:hover { background: #30434d; }
QPushButton#buildButton { background: #7d1d29; border-color: #ff4655; font-weight: 700; padding: 12px 20px; }
QPushButton#buildButton:hover { background: #a22534; }
QPushButton#sectionButton { text-align: left; color: #f2d84b; font-weight: 700; }
QHeaderView::section { background: #242a31; color: #f2d84b; padding: 6px; border: 0; }
QScrollArea { border: 0; }
"""


DEPENDENCY_TIPS = {
    "Cyberpunk 2077": (
        "Read-only source for the game archives. Install through Steam, GOG, or Epic, "
        "then select the Cyberpunk 2077 installation folder above."
    ),
    "Appearance Menu Mod": (
        "Required to spawn and customize the generated NPV in game. "
        "Download: https://www.nexusmods.com/cyberpunk2077/mods/790"
    ),
    "Codeware": (
        "In-game dependency of Appearance Creator Mod. It is not used to build the NPV ZIP. "
        "Download: https://www.nexusmods.com/cyberpunk2077/mods/7780"
    ),
    "Blender": (
        "Bakes V's selected head morphs without interactive dialogs. "
        "Download: https://www.blender.org/download/"
    ),
    "WolvenKit Blender IO Suite": (
        "Adds Cyberpunk import/export support to Blender. "
        "Download: https://github.com/WolvenKit/Cyberpunk-Blender-add-on/releases"
    ),
    "WolvenKit desktop": (
        "Optional GUI for manually inspecting REDengine resources. "
        "Download: https://github.com/WolvenKit/WolvenKit/releases"
    ),
    "WolvenKit CLI": (
        "Required for resource conversion, validation, and archive packing. "
        "Download WolvenKit.Console for Windows: https://github.com/WolvenKit/WolvenKit/releases"
    ),
    "NPV template resources": (
        "Prepared legal source project containing the NPV app, entity, meshes, rigs, and morph targets. "
        "Download: https://www.nexusmods.com/cyberpunk2077/mods/8328"
    ),
}

DEPENDENCY_LINKS = {
    "Cyberpunk 2077": "https://store.steampowered.com/app/1091500/Cyberpunk_2077/",
    "Appearance Menu Mod": "https://www.nexusmods.com/cyberpunk2077/mods/790",
    "Appearance Creator Mod": "https://www.nexusmods.com/cyberpunk2077/mods/10795",
    "Codeware": "https://www.nexusmods.com/cyberpunk2077/mods/7780",
    "Blender": "https://www.blender.org/download/",
    "WolvenKit Blender IO Suite": "https://github.com/WolvenKit/Cyberpunk-Blender-add-on/releases",
    "WolvenKit": "https://github.com/WolvenKit/WolvenKit/releases",
    "WolvenKit CLI": "https://github.com/WolvenKit/WolvenKit/releases",
    "NPV template resources": "https://www.nexusmods.com/cyberpunk2077/mods/8328",
}


class FinalBuildWorker(QObject):
    progress = Signal(str)
    completed = Signal(object)
    failed = Signal(object)

    def __init__(self, settings: AppSettings, character: CharacterConfig) -> None:
        super().__init__()
        self.settings = settings
        self.character = character

    @Slot()
    def run(self) -> None:
        try:
            result = FinalBuildBuilder(
                self.settings,
                execute=True,
                progress_callback=self.progress.emit,
            ).build(self.character)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit({"message": str(exc), "traceback": traceback.format_exc()})


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: AppSettings,
        *,
        settings_path: Path = DEFAULT_SETTINGS_PATH,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.settings_path = Path(settings_path)
        self.guard = PathGuard(settings.game_root, settings.workspace_root)
        self.game_data = load_game_data("2.3")
        self.path_edits: dict[str, QLineEdit] = {}
        self.setWindowTitle("NPV Studio 1.5.2 - Vortex NPV Builder")
        self.resize(1120, 900)
        self.setStyleSheet(CYBERPUNK_STYLE)
        self._build_ui()
        self.refresh_dependencies()
        self.refresh_presets()
        self._load_configured_character_source()

    def _build_ui(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)

        title = QLabel("NPV STUDIO")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color:#f2d84b;")
        subtitle = QLabel(
            "Configure V from top to bottom, verify dependencies, and export a Vortex-ready NPV ZIP."
        )
        subtitle.setStyleSheet("color:#9da7b1;")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        self._add_dependencies_section(layout)
        self._add_identity_and_presets(layout)
        self._add_character_builder(layout)
        self._add_output_section(layout)
        self._add_build_section(layout)
        layout.addStretch(1)

        scroll.setWidget(page)
        outer.addWidget(scroll, 1)
        self.setCentralWidget(central)

    def _add_dependencies_section(self, layout: QVBoxLayout) -> None:
        self.dependency_container = QFrame()
        self.dependency_container.setObjectName("dependencyContainer")
        container_layout = QVBoxLayout(self.dependency_container)
        container_layout.setContentsMargins(8, 8, 8, 8)

        self.dependency_toggle = QPushButton("▼ Dependencies and Paths")
        self.dependency_toggle.setObjectName("sectionButton")
        self.dependency_toggle.clicked.connect(self._toggle_dependencies)
        container_layout.addWidget(self.dependency_toggle)

        self.dependency_panel = QWidget()
        panel_layout = QVBoxLayout(self.dependency_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        self.safety_label = QLabel()
        self.safety_label.setWordWrap(True)
        self.safety_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.safety_label.setStyleSheet(
            "background:#182b2c; color:#72f1e8; border:1px solid #1bd9cf; padding:10px; font-weight:600;"
        )
        panel_layout.addWidget(self.safety_label)

        paths = QGroupBox("Dependency and workspace paths")
        self.dependency_paths_group = paths
        grid = QGridLayout(paths)
        path_specs = [
            ("game_root", "Cyberpunk installation folder", "folder"),
            ("workspace_root", "Writable build workspace", "folder"),
            ("blender_executable", "Blender executable", "exe"),
            ("blender_addon_root", "WolvenKit Blender IO Suite folder", "folder"),
            ("wolvenkit_gui_executable", "WolvenKit desktop executable", "exe"),
            ("wolvenkit_executable", "WolvenKit CLI executable", "exe"),
            ("npv_template_root", "Reusable NPV template folder", "folder"),
        ]
        for row, (key, label, picker_type) in enumerate(path_specs):
            edit = QLineEdit(str(getattr(self.settings, key) or ""))
            edit.setToolTip(
                "Automatic detection uses this configured path first. Choose a replacement here if detection fails."
            )
            button = QPushButton("Browse...")
            if picker_type == "folder":
                button.clicked.connect(partial(self._browse_directory, key))
            else:
                button.clicked.connect(partial(self._browse_executable, key))
            self.path_edits[key] = edit
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(edit, row, 1)
            grid.addWidget(button, row, 2)

        controls = QHBoxLayout()
        save_paths = QPushButton("Save Paths and Refresh")
        save_paths.clicked.connect(self.save_path_settings)
        self.refresh_button = QPushButton("Refresh Dependencies")
        self.refresh_button.clicked.connect(self._refresh_from_path_fields)
        controls.addWidget(save_paths)
        controls.addWidget(self.refresh_button)
        controls.addStretch(1)
        grid.addLayout(controls, len(path_specs), 0, 1, 3)
        self.dependency_table = QTableWidget(0, 4)
        self.dependency_table.setHorizontalHeaderLabels(
            ["Dependency (hover for details)", "Status", "Detected path", "Purpose"]
        )
        self.dependency_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.dependency_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.dependency_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.dependency_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.dependency_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.dependency_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.dependency_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.dependency_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.dependency_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        panel_layout.addWidget(self.dependency_table)

        links = QGroupBox("Resource links — click to open or highlight to copy")
        self.resource_links_group = links
        links_layout = QGridLayout(links)
        for row, (name, url) in enumerate(DEPENDENCY_LINKS.items()):
            links_layout.addWidget(QLabel(name), row, 0)
            link = QLabel(f'<a href="{url}" style="color:#72f1e8;">{url}</a>')
            link.setOpenExternalLinks(True)
            link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            links_layout.addWidget(link, row, 1)
        panel_layout.addWidget(links)
        panel_layout.addWidget(paths)

        container_layout.addWidget(self.dependency_panel)
        layout.addWidget(self.dependency_container)

    def _add_identity_and_presets(self, layout: QVBoxLayout) -> None:
        identity = QGroupBox("1. Character identity and files")
        form = QFormLayout(identity)
        self.name_edit = QLineEdit("My V")
        self.namespace_edit = QLineEdit("my_v")
        self.frame_combo = QComboBox()
        self.frame_combo.addItem("Feminine base frame", BodyFrame.FEMALE.value)
        self.frame_combo.addItem("Masculine base frame", BodyFrame.MALE.value)
        form.addRow("NPV display name", self.name_edit)
        form.addRow("Unique namespace", self.namespace_edit)
        form.addRow("Body frame", self.frame_combo)

        preset_directory = QHBoxLayout()
        self.preset_root_edit = QLineEdit(
            str(self.settings.preset_root or self.settings.workspace_root / "presets")
        )
        preset_browse = QPushButton("Choose preset folder...")
        preset_browse.clicked.connect(self._browse_preset_root)
        preset_directory.addWidget(self.preset_root_edit, 1)
        preset_directory.addWidget(preset_browse)
        form.addRow("Preset save folder", preset_directory)
        preset_note = QLabel(
            "This folder contains reusable JSON character presets only. It does not contain game files or Vortex mods."
        )
        preset_note.setWordWrap(True)
        preset_note.setStyleSheet("color:#9da7b1;")
        form.addRow(preset_note)

        preset_controls = QHBoxLayout()
        self.preset_combo = QComboBox()
        save_button = QPushButton("Save Current Preset")
        load_button = QPushButton("Load Selected Preset")
        import_button = QPushButton("Load Character File...")
        save_button.clicked.connect(self.save_preset)
        load_button.clicked.connect(self.load_preset)
        import_button.clicked.connect(self.load_character_file)
        preset_controls.addWidget(self.preset_combo, 1)
        preset_controls.addWidget(save_button)
        preset_controls.addWidget(load_button)
        preset_controls.addWidget(import_button)
        form.addRow("Saved presets", preset_controls)
        layout.addWidget(identity)

    def _add_character_builder(self, layout: QVBoxLayout) -> None:
        builder = QGroupBox("2. Character creator selections (in-game order)")
        form = QFormLayout(builder)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.detail_spins: dict[str, QSpinBox] = {}
        self.creator_widgets: dict[str, QWidget] = {}
        self.creator_labels: dict[str, QLabel] = {}

        self.skin_tone_spin = self._spin("skin_tone")
        self.skin_type_spin = self._spin("skin_type")
        self.hairstyle_spin = self._spin("hairstyle")
        self.hair_color_spin = self._spin("hair_color")
        self.eyes_spin = self._spin("eyes")
        self.eye_color_spin = self._spin("eye_color")
        self.nose_spin = self._spin("nose")
        self.mouth_spin = self._spin("mouth")
        self.jaw_spin = self._spin("jaw")
        self.ears_spin = self._spin("ears")

        specs: list[tuple[str, str, QWidget]] = [
            ("Skin tone", "skin_tone", self.skin_tone_spin),
            ("Skin type", "skin_type", self.skin_type_spin),
            ("Hairstyle", "hairstyle", self.hairstyle_spin),
            ("Hair color", "hair_color", self.hair_color_spin),
            ("Eyes", "eyes", self.eyes_spin),
            ("Eye color", "eye_color", self.eye_color_spin),
            ("Eyebrows", "eyebrows", self._detail_spin("eyebrows")),
            ("Eyebrow color", "eyebrow_color", self._detail_spin("eyebrow_color")),
            ("Eyelash color", "eyelash_color", self._detail_spin("eyelash_color")),
            ("Nose", "nose", self.nose_spin),
            ("Mouth", "mouth", self.mouth_spin),
            ("Jaw", "jaw", self.jaw_spin),
            ("Ears", "ears", self.ears_spin),
            ("Beard", "beard", self._detail_spin("beard")),
            ("Beard style", "beard_style", self._detail_spin("beard_style")),
            ("Beard color", "beard_color", self._detail_spin("beard_color")),
            ("Cyberware", "cyberware", self._detail_spin("cyberware")),
            ("Facial scars", "facial_scars", self._detail_spin("facial_scars")),
            ("Facial tattoos", "facial_tattoos", self._detail_spin("facial_tattoos")),
            ("Piercings", "piercings", self._detail_spin("piercings")),
            ("Piercing color", "piercing_color", self._detail_spin("piercing_color")),
            ("Teeth", "teeth", self._detail_spin("teeth")),
            ("Eye makeup", "eye_makeup", self._detail_spin("eye_makeup")),
            ("Eye makeup color", "eye_makeup_color", self._detail_spin("eye_makeup_color")),
        ]

        self.lip_finish_combo = QComboBox()
        for value in ("off", "default", "glossy", "matte"):
            self.lip_finish_combo.addItem(value.title(), value)
        specs.extend(
            [
                ("Lip makeup style", "lip_makeup_finish", self.lip_finish_combo),
                ("Lip makeup", "lip_makeup", self._detail_spin("lip_makeup")),
                ("Lip makeup color", "lip_makeup_color", self._detail_spin("lip_makeup_color")),
                ("Cheek makeup", "cheek_makeup", self._detail_spin("cheek_makeup")),
                ("Cheek makeup color", "cheek_makeup_color", self._detail_spin("cheek_makeup_color")),
                ("Blemishes", "blemishes", self._detail_spin("blemishes")),
                ("Blemish color", "blemish_color", self._detail_spin("blemish_color")),
            ]
        )

        self.nail_style_combo = QComboBox()
        for value in ("short", "long"):
            self.nail_style_combo.addItem(value.title(), value)
        specs.append(("Nails", "nail_style", self.nail_style_combo))
        specs.append(("Nail color", "nail_color", self._detail_spin("nail_color")))

        self.chest_combo = QComboBox()
        for value in ("default", "small", "big"):
            self.chest_combo.addItem(value.title(), value)
        specs.extend(
            [
                ("Chest", "chest", self.chest_combo),
                ("Nipples", "nipples", self._detail_spin("nipples")),
                ("Body tattoos", "body_tattoos", self._detail_spin("body_tattoos")),
                ("Body scars", "body_scars", self._detail_spin("body_scars")),
            ]
        )

        self.genitals_combo = QComboBox()
        for label, value in (
            ("None", "none"),
            ("Vagina", "vagina"),
            ("Penis 1 — manual AMM toggle", "penis_1"),
            ("Penis 2 — manual AMM toggle", "penis_2"),
        ):
            self.genitals_combo.addItem(label, value)
        self.penis_size_combo = QComboBox()
        for value in ("unavailable", "small", "default", "big"):
            self.penis_size_combo.addItem(value.title(), value)
        specs.extend(
            [
                ("Genitals", "genitals", self.genitals_combo),
                ("Penis size", "penis_size", self.penis_size_combo),
                ("Pubic hair style", "pubic_hair_style", self._detail_spin("pubic_hair_style")),
                ("Pubic hair color", "pubic_hair_color", self._detail_spin("pubic_hair_color")),
            ]
        )

        for number, (label, key, widget) in enumerate(specs, 1):
            label_widget = QLabel(f"{number:02d}. {label}")
            self.creator_widgets[key] = widget
            self.creator_labels[key] = label_widget
            form.addRow(label_widget, widget)
        layout.addWidget(builder)
        self._connect_creator_conditions()
        self._update_creator_conditions()

    def _connect_creator_conditions(self) -> None:
        self.frame_combo.currentIndexChanged.connect(self._update_creator_conditions)
        self.lip_finish_combo.currentIndexChanged.connect(self._update_creator_conditions)
        for key in (
            "eyebrows",
            "beard",
            "piercings",
            "eye_makeup",
            "lip_makeup",
            "cheek_makeup",
            "blemishes",
            "pubic_hair_style",
        ):
            self.detail_spins[key].valueChanged.connect(self._update_creator_conditions)
        self.genitals_combo.currentIndexChanged.connect(self._update_creator_conditions)

    def _set_creator_available(
        self,
        key: str,
        available: bool,
        dependency: str,
        requirement: str,
    ) -> None:
        widget = self.creator_widgets[key]
        label = self.creator_labels[key]
        widget.setEnabled(available)
        label.setEnabled(available)
        state = (
            f"Available because {requirement}."
            if available
            else f"Unavailable until {requirement}."
        )
        dependency_tip = f"Depends on {dependency}. {state}"
        range_tip = str(widget.property("rangeTip") or "")
        widget.setToolTip(
            f"{dependency_tip}\n{range_tip}" if range_tip else dependency_tip
        )
        label.setToolTip(dependency_tip)

    def _update_creator_conditions(self, *_args: object) -> None:
        if getattr(self, "_setting_character", False):
            return
        masculine = self.frame_combo.currentData() == BodyFrame.MALE.value
        if masculine:
            self.chest_combo.setCurrentIndex(max(0, self.chest_combo.findData("default")))
            self.detail_spins["nipples"].setValue(0)
        else:
            self.detail_spins["beard"].setValue(0)
        self._set_creator_available(
            "chest", not masculine, "Body frame", "the feminine body frame is selected"
        )
        self._set_creator_available(
            "nipples", not masculine, "Body frame", "the feminine body frame is selected"
        )
        self._set_creator_available(
            "beard", masculine, "Body frame", "the masculine body frame is selected"
        )
        beard_shape = self.detail_spins["beard"].value()
        beard_style = self.detail_spins["beard_style"]
        valid_styles = BEARD_STYLE_CHUNK_MASKS.get(beard_shape, {1: 1})
        beard_style.setMaximum(max(valid_styles))
        if beard_style.value() not in valid_styles:
            beard_style.setValue(min(valid_styles))
        self._set_creator_available(
            "beard_style",
            masculine and beard_shape in BEARD_STYLE_CHUNK_MASKS and len(valid_styles) > 1,
            "Beard",
            "a masculine beard shape with multiple styles is selected",
        )
        self._set_creator_available(
            "beard_color",
            masculine and beard_shape > 1,
            "Beard",
            "a masculine beard shape with colorable geometry is selected",
        )

        primary_rules = {
            "eyebrow_color": (self.detail_spins["eyebrows"].value() > 0, "Eyebrows"),
            "piercing_color": (self.detail_spins["piercings"].value() > 0, "Piercings"),
            "eye_makeup_color": (self.detail_spins["eye_makeup"].value() > 0, "Eye makeup"),
            "cheek_makeup_color": (self.detail_spins["cheek_makeup"].value() > 0, "Cheek makeup"),
            "blemish_color": (self.detail_spins["blemishes"].value() > 0, "Blemishes"),
            "pubic_hair_color": (self.detail_spins["pubic_hair_style"].value() > 0, "Pubic hair style"),
        }
        for key, (available, dependency) in primary_rules.items():
            self._set_creator_available(
                key, available, dependency, f"{dependency} is enabled"
            )

        cheek_style = self.detail_spins["cheek_makeup"].value()
        cheek_color = self.detail_spins["cheek_makeup_color"]
        # Vanilla creator choices 01-04 are freckle styles with four colors;
        # choices 05-14 are cheek makeup with eight colors.
        cheek_color.setMaximum(4 if 1 <= cheek_style <= 4 else 8)
        cheek_range = (
            "Styles 01-04 use the vanilla freckle palette: colors 1-4."
            if 1 <= cheek_style <= 4
            else "Styles 05-14 use the vanilla cheek palette: colors 1-8."
        )
        cheek_color.setProperty("rangeTip", cheek_range)
        if cheek_color.isEnabled():
            cheek_color.setToolTip(
                "Depends on Cheek makeup. Available because Cheek makeup is enabled.\n"
                f"{cheek_range}"
            )

        lip_style_enabled = self.lip_finish_combo.currentData() != "off"
        if not lip_style_enabled:
            self.detail_spins["lip_makeup"].setValue(0)
        self._set_creator_available(
            "lip_makeup",
            lip_style_enabled,
            "Lip makeup style",
            "Lip makeup style is not Off",
        )
        self._set_creator_available(
            "lip_makeup_color",
            lip_style_enabled and self.detail_spins["lip_makeup"].value() > 0,
            "Lip makeup",
            "Lip makeup style and Lip makeup are not Off",
        )

        penis_selected = str(self.genitals_combo.currentData()).startswith("penis")
        if not penis_selected:
            self.penis_size_combo.setCurrentIndex(
                max(0, self.penis_size_combo.findData("unavailable"))
            )
        elif self.penis_size_combo.currentData() == "unavailable":
            self.penis_size_combo.setCurrentIndex(
                max(0, self.penis_size_combo.findData("default"))
            )
        self._set_creator_available(
            "penis_size",
            penis_selected,
            "Genitals",
            "Penis 1 or Penis 2 is selected under Genitals",
        )
        genitals_selected = self.genitals_combo.currentData() != "none"
        if not genitals_selected:
            self.detail_spins["pubic_hair_style"].setValue(0)
        self._set_creator_available(
            "pubic_hair_style",
            genitals_selected,
            "Genitals",
            "Vagina, Penis 1, or Penis 2 is selected under Genitals",
        )
        self._set_creator_available(
            "pubic_hair_color",
            genitals_selected and self.detail_spins["pubic_hair_style"].value() > 0,
            "Pubic hair style",
            "a genital geometry and pubic-hair style are selected",
        )

    def _add_output_section(self, layout: QVBoxLayout) -> None:
        output = QGroupBox("3. Generated NPV options and save location")
        form = QFormLayout(output)
        self.starter_outfit_check = QCheckBox(
            "Include V's tattered shirt, pants, and sneakers in the default appearance"
        )
        self.starter_outfit_check.setChecked(True)
        self.base_body_check = QCheckBox(
            "Include base-body and feminine dual-body toggles for ACM customization"
        )
        self.base_body_check.setChecked(True)
        self.acm_slots_check = QCheckBox(
            "Include empty ACM slots: 5 each for face/head/torso/legs/item and 2 each for hands/arms/feet"
        )
        self.acm_slots_check.setChecked(True)
        form.addRow(self.starter_outfit_check)
        form.addRow(self.base_body_check)
        form.addRow(self.acm_slots_check)

        public_appearance = QLineEdit("default")
        public_appearance.setReadOnly(True)
        public_appearance.setToolTip(
            "Production NPVs publish one AMM appearance named default. The tutorial business appearance is removed."
        )
        form.addRow("AMM appearance name", public_appearance)

        export_directory = QHBoxLayout()
        self.package_output_edit = QLineEdit(
            str(
                self.settings.package_output_root
                or self.settings.workspace_root / "packages"
            )
        )
        export_browse = QPushButton("Choose ZIP export folder...")
        export_browse.clicked.connect(self._browse_package_output_root)
        export_directory.addWidget(self.package_output_edit, 1)
        export_directory.addWidget(export_browse)
        form.addRow("Vortex ZIP export folder", export_directory)
        export_note = QLabel(
            "This folder receives the completed Vortex-installable ZIP and a small manifest containing its checksum. "
            "NPV Studio never installs the ZIP or writes into Vortex staging."
        )
        export_note.setWordWrap(True)
        export_note.setStyleSheet("color:#72f1e8;")
        form.addRow(export_note)
        layout.addWidget(output)

    def _add_build_section(self, layout: QVBoxLayout) -> None:
        build = QGroupBox("4. Validate and build")
        build_layout = QVBoxLayout(build)
        note = QLabel(
            "Validation runs first. Selections without an available asset mapping stop before Blender and WolvenKit; a ZIP is produced only after all stages succeed."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#f2b84b;")
        build_layout.addWidget(note)

        self.activity_label = QLabel("Build activity will appear here.")
        self.activity_label.setStyleSheet("color:#1bd9cf; font-family:Consolas; font-weight:700;")
        self.activity_label.setVisible(False)
        build_layout.addWidget(self.activity_label)

        self.activity_symbols = ("—", "\\", "|", "/", "—", "/", "|", "\\")
        self.activity_symbol_index = 0
        self.activity_message = ""
        self.activity_elapsed = QElapsedTimer()
        self.activity_elapsed_frozen_ms: int | None = None
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(120)
        self.activity_timer.timeout.connect(self._advance_activity_spinner)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMinimumHeight(220)
        self.output_log.setPlaceholderText("Validation and build results will appear here.")
        build_layout.addWidget(self.output_log)

        buttons = QHBoxLayout()
        validate = QPushButton("Validate Configuration")
        validate.clicked.connect(self.validate_configuration)
        self.build_button = QPushButton("Build Vortex ZIP")
        self.build_button.setObjectName("buildButton")
        self.build_button.clicked.connect(self.generate_build)
        buttons.addStretch(1)
        buttons.addWidget(validate)
        buttons.addWidget(self.build_button)
        build_layout.addLayout(buttons)
        layout.addWidget(build)

    def _spin(self, key: str, value: int = 1) -> QSpinBox:
        minimum, maximum = selector_range(self.game_data, key)
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        range_tip = f"Cyberpunk 2077 2.3 selector range: {minimum}-{maximum}"
        spin.setProperty("rangeTip", range_tip)
        spin.setToolTip(range_tip)
        return spin

    def _detail_spin(self, key: str) -> QSpinBox:
        if key in self.detail_spins:
            return self.detail_spins[key]
        overrides = {
            "eyebrow_color": (1, 35),
            "beard": (0, 12),
            "beard_style": (1, 7),
            "beard_color": (1, 35),
            "eye_makeup_color": (1, 14),
            "lip_makeup_color": (1, 14),
            "blemish_color": (1, 6),
            "nipples": (0, 3),
            "nail_color": (1, 37),
        }
        if key in overrides:
            minimum, maximum = overrides[key]
        else:
            minimum, maximum = selector_range(self.game_data, key)
        default = 11 if key == "nail_color" else minimum
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(default)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        range_tip = f"Cyberpunk 2077 2.3 selector range: {minimum}-{maximum}"
        spin.setProperty("rangeTip", range_tip)
        spin.setToolTip(range_tip)
        self.detail_spins[key] = spin
        return spin

    def _toggle_dependencies(self) -> None:
        visible = self.dependency_panel.isHidden()
        self.dependency_panel.setVisible(visible)
        marker = "▼" if visible else "▶"
        summary = getattr(self, "dependency_summary", "Dependencies and Paths")
        self.dependency_toggle.setText(f"{marker} {summary}")

    def _browse_directory(self, key: str) -> None:
        current = self.path_edits[key].text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select folder", current)
        if selected:
            self.path_edits[key].setText(selected)

    def _browse_executable(self, key: str) -> None:
        current = self.path_edits[key].text().strip()
        start = str(Path(current).parent) if current else str(Path.home())
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select executable", start, "Executables (*.exe);;All files (*)"
        )
        if selected:
            self.path_edits[key].setText(selected)

    def _browse_preset_root(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Select preset folder", self.preset_root_edit.text()
        )
        if selected:
            self.preset_root_edit.setText(selected)
            if self.save_path_settings(show_message=False):
                self.refresh_presets()

    def _browse_package_output_root(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Select Vortex ZIP export folder", self.package_output_edit.text()
        )
        if selected:
            self.package_output_edit.setText(selected)
            self.save_path_settings(show_message=False)

    def save_path_settings(self, _checked: bool = False, *, show_message: bool = True) -> bool:
        try:
            values: dict[str, object] = {}
            for key, edit in self.path_edits.items():
                text = edit.text().strip()
                values[key] = Path(text) if text else None
            values["preset_root"] = Path(self.preset_root_edit.text().strip())
            values["package_output_root"] = Path(self.package_output_edit.text().strip())
            values["install_enabled"] = False
            updated = self.settings.model_copy(update=values)
            updated = AppSettings.model_validate(updated.model_dump())
            updated.workspace_root.mkdir(parents=True, exist_ok=True)
            guard = PathGuard(updated.game_root, updated.workspace_root)
            guard.ensure_export_directory(updated.preset_root or updated.workspace_root / "presets")
            guard.ensure_export_directory(
                updated.package_output_root or updated.workspace_root / "packages"
            )
            save_settings(updated, self.settings_path)
            self.settings = updated
            self.guard = guard
            self._refresh_safety_label()
            self.refresh_dependencies()
            if show_message:
                QMessageBox.information(
                    self,
                    "Paths saved",
                    f"Configuration saved to:\n{self.settings_path}",
                )
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Could not save paths", str(exc))
            return False

    def _refresh_from_path_fields(self) -> None:
        """Persist the visible path selections and immediately rescan them."""
        self.save_path_settings(show_message=False)

    def _refresh_safety_label(self) -> None:
        preset_root = self.settings.preset_root or self.settings.workspace_root / "presets"
        package_root = self.settings.package_output_root or self.settings.workspace_root / "packages"
        self.safety_label.setText(
            f"READ-ONLY GAME SOURCE: {self.settings.game_root}\n"
            f"WRITABLE BUILD WORKSPACE: {self.settings.workspace_root}\n"
            f"PRESETS: {preset_root}\n"
            f"VORTEX ZIP EXPORTS: {package_root}"
        )

    def refresh_dependencies(self) -> None:
        self._refresh_safety_label()
        statuses = DependencyInspector(self.settings, self.guard).inspect()
        build_statuses = [item for item in statuses if item.kind is DependencyKind.BUILD]
        ready = sum(item.available for item in build_statuses)
        self.dependency_summary = (
            f"Dependencies and Paths - {ready}/{len(build_statuses)} build requirements ready"
        )
        marker = "▼" if not self.dependency_panel.isHidden() else "▶"
        self.dependency_toggle.setText(f"{marker} {self.dependency_summary}")
        self.dependency_table.setRowCount(len(statuses))
        for row, dependency in enumerate(statuses):
            if dependency.kind is DependencyKind.RUNTIME_MOD:
                state = "INSTALLED" if dependency.available else "INSTALL MOD"
            elif dependency.kind is DependencyKind.OPTIONAL:
                state = "AVAILABLE" if dependency.available else "OPTIONAL"
            else:
                state = "READY" if dependency.available else "NOT FOUND"
            tip = DEPENDENCY_TIPS.get(dependency.name, dependency.details)
            values = [
                dependency.name,
                state,
                str(dependency.path or "-"),
                dependency.details,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(f"{tip}\n\nDetected status: {state}\n{dependency.details}")
                if column == 1:
                    if dependency.available:
                        item.setForeground(Qt.GlobalColor.green)
                    elif dependency.kind is DependencyKind.OPTIONAL:
                        item.setForeground(Qt.GlobalColor.lightGray)
                    else:
                        item.setForeground(Qt.GlobalColor.yellow)
                self.dependency_table.setItem(row, column, item)
        table_height = (
            self.dependency_table.horizontalHeader().sizeHint().height()
            + self.dependency_table.verticalHeader().length()
            + self.dependency_table.frameWidth() * 2
            + 4
        )
        self.dependency_table.setFixedHeight(table_height)

    def current_character(self) -> CharacterConfig:
        # QSpinBox.value() can still contain the previous value while the user is
        # actively editing its line edit. Commit every visible numeric editor so
        # Build/Save always captures exactly what is displayed in the interface.
        for spin in self.findChildren(QSpinBox):
            spin.interpretText()
        details = {name: widget.value() for name, widget in self.detail_spins.items()}
        return CharacterConfig(
            name=self.name_edit.text(),
            namespace=self.namespace_edit.text(),
            body_frame=BodyFrame(self.frame_combo.currentData()),
            # NPVs do not participate in player dialogue. Retain a derived value
            # only for backward-compatible preset files; it is not user-facing.
            voice=(
                VoiceTone.FEMININE
                if BodyFrame(self.frame_combo.currentData()) is BodyFrame.FEMALE
                else VoiceTone.MASCULINE
            ),
            head=HeadShape(
                eyes=self.eyes_spin.value(),
                nose=self.nose_spin.value(),
                mouth=self.mouth_spin.value(),
                jaw=self.jaw_spin.value(),
                ears=self.ears_spin.value(),
            ),
            appearance=AppearanceSelection(
                skin_tone=self.skin_tone_spin.value(),
                skin_type=self.skin_type_spin.value(),
                hairstyle=self.hairstyle_spin.value(),
                hair_color=self.hair_color_spin.value(),
                eye_color=self.eye_color_spin.value(),
                chest=self.chest_combo.currentData(),
                nail_style=self.nail_style_combo.currentData(),
                lip_makeup_finish=self.lip_finish_combo.currentData(),
                genitals=self.genitals_combo.currentData(),
                penis_size=self.penis_size_combo.currentData(),
                **details,
            ),
            output=OutputOptions(
                base_body=self.base_body_check.isChecked(),
                starter_outfit=self.starter_outfit_check.isChecked(),
                acm_slots=self.acm_slots_check.isChecked(),
                appearance_name="default",
            ),
        )

    def set_character(self, character: CharacterConfig) -> None:
        self._setting_character = True
        self.name_edit.setText(character.name)
        self.namespace_edit.setText(character.namespace)
        self.frame_combo.setCurrentIndex(max(0, self.frame_combo.findData(character.body_frame.value)))
        for key in ("eyes", "nose", "mouth", "jaw", "ears"):
            getattr(self, f"{key}_spin").setValue(getattr(character.head, key))
        for key in ("skin_tone", "skin_type", "hairstyle", "hair_color", "eye_color"):
            getattr(self, f"{key}_spin").setValue(getattr(character.appearance, key))
        for key, widget in self.detail_spins.items():
            widget.setValue(getattr(character.appearance, key))
        self.chest_combo.setCurrentIndex(
            max(0, self.chest_combo.findData(character.appearance.chest))
        )
        self.nail_style_combo.setCurrentIndex(
            max(0, self.nail_style_combo.findData(character.appearance.nail_style))
        )
        self.lip_finish_combo.setCurrentIndex(
            max(
                0,
                self.lip_finish_combo.findData(
                    "off"
                    if character.appearance.lip_makeup == 0
                    else character.appearance.lip_makeup_finish
                ),
            )
        )
        self.genitals_combo.setCurrentIndex(
            max(0, self.genitals_combo.findData(character.appearance.genitals))
        )
        self.penis_size_combo.setCurrentIndex(
            max(0, self.penis_size_combo.findData(character.appearance.penis_size))
        )
        self.base_body_check.setChecked(character.output.base_body)
        self.starter_outfit_check.setChecked(character.output.starter_outfit)
        self.acm_slots_check.setChecked(character.output.acm_slots)
        self._setting_character = False
        self._update_creator_conditions()

    def validate_configuration(self) -> None:
        if not self.save_path_settings(show_message=False):
            return
        try:
            character = self.current_character()
            FinalBuildBuilder(self.settings).validate_character(character)
            self.output_log.setPlainText(
                "VALIDATION PASSED\n"
                f"Character: {character.name}\n"
                f"Frame: {character.body_frame.value}\n"
                "The configuration is ready for the full Blender and WolvenKit build."
            )
        except Exception as exc:
            self.output_log.setPlainText(f"VALIDATION FAILED\n{exc}")
            QMessageBox.critical(self, "Validation failed", str(exc))

    def generate_build(self) -> None:
        if not self.save_path_settings(show_message=False):
            return
        character = self.current_character()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        self.debug_log_path = self.guard.assert_write_path(
            self.settings.workspace_root / "logs" / f"studio-build-{stamp}.log"
        )
        diagnostic = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "python": sys.executable,
            "ui_module": str(Path(__file__).resolve()),
            "final_builder_module": str(
                Path(sys.modules[FinalBuildBuilder.__module__].__file__).resolve()
            ),
            "character": character.model_dump(mode="json"),
            "game_access": "read_only",
            "workspace": str(self.settings.workspace_root),
            "package_output_root": str(self.settings.package_output_root),
        }
        self.guard.write_text(
            self.debug_log_path,
            "NPV STUDIO BUILD DEBUG LOG\n" + json.dumps(diagnostic, indent=2) + "\n\n",
        )
        try:
            FinalBuildBuilder(self.settings).validate_character(character)
        except Exception as exc:
            details = traceback.format_exc()
            self._append_debug(f"PRE-FLIGHT FAILED\n{details}")
            self.output_log.setPlainText(
                "PRE-FLIGHT FAILED\n"
                f"{exc}\n\nDebug log: {self.debug_log_path}"
            )
            QMessageBox.critical(
                self, "Build validation failed", f"{exc}\n\nDebug log:\n{self.debug_log_path}"
            )
            return

        self.build_button.setEnabled(False)
        self._start_activity("[1/9] Validating creator selections")
        self.output_log.setPlainText(
            "Configuration validated\n"
            f"Character: {character.name} ({character.body_frame.value})\n"
            f"Export folder: {self.settings.package_output_root}\n"
            f"Debug log: {self.debug_log_path}\n\n"
            "Starting final workspace-only build..."
        )
        self._append_debug("PRE-FLIGHT PASSED\nStarting final workspace-only build")
        self.build_thread = QThread(self)
        self.build_worker = FinalBuildWorker(self.settings, character)
        self.build_worker.moveToThread(self.build_thread)
        self.build_thread.started.connect(self.build_worker.run)
        self.build_worker.progress.connect(self._build_progress)
        self.build_worker.completed.connect(self._build_completed)
        self.build_worker.failed.connect(self._build_failed)
        self.build_worker.completed.connect(self.build_thread.quit)
        self.build_worker.failed.connect(self.build_thread.quit)
        self.build_thread.finished.connect(self.build_worker.deleteLater)
        self.build_thread.finished.connect(self.build_thread.deleteLater)
        self.build_thread.start()

    def _build_completed(self, report: dict) -> None:
        self._stop_activity("Build complete")
        package = report["package"]
        self.output_log.append(
            "\nBUILD COMPLETE\n"
            f"Vortex ZIP: {package['archive']}\n"
            f"SHA-256: {package['sha256']}\n"
            f"Files: {package['inspection']['file_count']}\n"
            "The ZIP was not installed and the game directory was not modified."
        )
        self._append_debug("BUILD COMPLETE\n" + json.dumps(report, indent=2))
        self.build_button.setEnabled(True)

    def _build_progress(self, message: str) -> None:
        self.activity_message = message
        self._render_activity_spinner()
        self.output_log.append(message)
        self._append_debug(f"PROGRESS: {message}")

    def _start_activity(self, message: str) -> None:
        self.activity_message = message
        self.activity_symbol_index = 0
        self.activity_elapsed_frozen_ms = None
        self.activity_elapsed.start()
        self.activity_label.setVisible(True)
        self._render_activity_spinner()
        self.activity_timer.start()

    def _advance_activity_spinner(self) -> None:
        self.activity_symbol_index = (
            self.activity_symbol_index + 1
        ) % len(self.activity_symbols)
        self._render_activity_spinner()

    def _render_activity_spinner(self) -> None:
        symbol = self.activity_symbols[self.activity_symbol_index]
        self.activity_label.setText(
            f"{symbol}  Elapsed {self._activity_elapsed_text()}  |  {self.activity_message}"
        )

    def _activity_elapsed_text(self) -> str:
        elapsed_ms = self.activity_elapsed_frozen_ms
        if elapsed_ms is None:
            elapsed_ms = self.activity_elapsed.elapsed() if self.activity_elapsed.isValid() else 0
        total_tenths = max(0, elapsed_ms) // 100
        hours, remainder = divmod(total_tenths, 36_000)
        minutes, remainder = divmod(remainder, 600)
        seconds, tenths = divmod(remainder, 10)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{tenths}"
        return f"{minutes:02d}:{seconds:02d}.{tenths}"

    def _stop_activity(self, message: str) -> None:
        self.activity_elapsed_frozen_ms = (
            self.activity_elapsed.elapsed() if self.activity_elapsed.isValid() else 0
        )
        self.activity_timer.stop()
        self.activity_label.setText(
            f"Elapsed {self._activity_elapsed_text()}  |  {message}"
        )
        self.activity_label.setVisible(True)

    def _append_debug(self, text: str) -> None:
        if not hasattr(self, "debug_log_path"):
            return
        with self.debug_log_path.open("a", encoding="utf-8") as log:
            log.write(text.rstrip() + "\n")

    def _build_failed(self, failure: dict) -> None:
        self._stop_activity("Build stopped — see the failure details below")
        message = str(failure.get("message", "Unknown build error"))
        details = str(failure.get("traceback", message))
        self._append_debug(f"BUILD FAILED\n{details}")
        self.output_log.append(
            f"\nBUILD FAILED\n{message}\n\nFull traceback: {self.debug_log_path}"
        )
        self.build_button.setEnabled(True)
        QMessageBox.critical(
            self, "Build failed", f"{message}\n\nFull debug log:\n{self.debug_log_path}"
        )

    def load_character_file(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Load character configuration",
            str(self.settings.character_source_path or self._preset_root()),
            "Character files (*.txt *.json);;All files (*)",
        )
        if not path:
            return
        try:
            character = load_character_config(Path(path))
            self.set_character(character)
            self.output_log.setPlainText(f"Loaded character configuration: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not load character file", str(exc))

    def _load_configured_character_source(self) -> None:
        source = self.settings.character_source_path
        if source is None or not source.is_file():
            return
        try:
            character = load_character_config(source)
            self.set_character(character)
            self.output_log.setPlainText(
                f"Loaded configured character source:\n{source}\n\n"
                f"Character: {character.name}\nFrame: {character.body_frame.value}"
            )
        except Exception as exc:
            self.output_log.setPlainText(
                f"Configured character source could not be loaded:\n{source}\n\n{exc}"
            )

    def _preset_root(self) -> Path:
        root = self.settings.preset_root or self.settings.workspace_root / "presets"
        return self.guard.ensure_export_directory(root)

    def refresh_presets(self) -> None:
        current = self.preset_combo.currentText() if hasattr(self, "preset_combo") else ""
        if not hasattr(self, "preset_combo"):
            return
        self.preset_combo.clear()
        for path in sorted(self._preset_root().glob("*.json")):
            self.preset_combo.addItem(path.stem, path)
        index = self.preset_combo.findText(current)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)

    def save_preset(self) -> None:
        if not self.save_path_settings(show_message=False):
            return
        try:
            character = self.current_character()
            root = self._preset_root()
            path = self.guard.assert_export_path(root / f"{character.namespace}.json", root)
            path.write_text(
                json.dumps(character.model_dump(mode="json"), indent=2) + "\n",
                encoding="utf-8",
            )
            self.refresh_presets()
            self.preset_combo.setCurrentText(character.namespace)
            self.output_log.setPlainText(f"Preset saved: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not save preset", str(exc))

    def load_preset(self) -> None:
        path = self.preset_combo.currentData()
        if not path:
            QMessageBox.information(self, "No preset", "Save or select a preset first.")
            return
        try:
            character = CharacterConfig.model_validate_json(
                Path(path).read_text(encoding="utf-8")
            )
            self.set_character(character)
            self.output_log.setPlainText(f"Preset loaded: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not load preset", str(exc))
