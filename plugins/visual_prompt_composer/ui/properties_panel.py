"""
Properties Panel

Interactive panel for editing visual tag properties, AI profiles, and descriptiveness settings.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QDoubleSpinBox, QSlider, QComboBox, QGroupBox, QFormLayout,
    QCheckBox, QTextEdit, QScrollArea, QFrame, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QGraphicsDropShadowEffect

from ..models.visual_tag import VisualTag, ElementType, DescriptorProfile, AIProfile
from ..models.scene_graph import Scene
from framework.modern_ui import apply_modern_style


class DescriptivenessSlider(QWidget):
    """Custom slider widget for controlling AI descriptiveness levels"""

    value_changed = pyqtSignal(float)  # descriptiveness_level

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()

    def _init_ui(self):
        """Initialize the descriptiveness slider UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("", 9, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # Slider with labels
        slider_layout = QHBoxLayout()

        # Min label
        min_label = QLabel("Minimal")
        min_label.setStyleSheet("color: #6c757d; font-size: 8px;")
        slider_layout.addWidget(min_label)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)  # Default to medium
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(25)
        slider_layout.addWidget(self.slider, 1)

        # Max label
        max_label = QLabel("Detailed")
        max_label.setStyleSheet("color: #6c757d; font-size: 8px;")
        slider_layout.addWidget(max_label)

        layout.addLayout(slider_layout)

        # Value display
        self.value_label = QLabel("50%")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("color: #007bff; font-weight: bold; font-size: 10px;")
        layout.addWidget(self.value_label)

        # Connect signals
        self.slider.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, value: int):
        """Handle slider value change"""
        self.value_label.setText(f"{value}%")
        self.value_changed.emit(value / 100.0)

    def set_value(self, value: float):
        """Set slider value (0.0 to 1.0)"""
        self.slider.setValue(int(value * 100))

    def get_value(self) -> float:
        """Get current slider value (0.0 to 1.0)"""
        return self.slider.value() / 100.0

    def add_shadow_effect(self):
        """Adds a drop shadow effect to the widget."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

        # A simple stylesheet to give the widget a body for the shadow to appear behind
        self.setStyleSheet("background-color: #3a3a3a; border-radius: 5px; padding: 5px;")


class AIProfileEditor(QWidget):
    """Widget for editing AI profile settings"""

    profile_changed = pyqtSignal(object)  # AIProfile

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_profile = AIProfile(DescriptorProfile.ANATOMICAL_PRECISE)
        self._init_ui()

    def _init_ui(self):
        """Initialize the AI profile editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Profile selection
        profile_group = QGroupBox("AI Description Style")
        profile_layout = QVBoxLayout(profile_group)

        # Profile buttons
        self.profile_buttons = QButtonGroup()

        profiles = [
            (DescriptorProfile.ANATOMICAL_PRECISE, "Anatomical/Precise", "Technical, precise descriptions focusing on structure and detail"),
            (DescriptorProfile.MATERIAL_STRUCTURAL, "Material/Structural", "Focus on materials, textures, and structural elements"),
            (DescriptorProfile.ATMOSPHERIC_MELLOW, "Atmospheric/Mellow", "Soft, ambient descriptions emphasizing mood and atmosphere"),
            (DescriptorProfile.EMOTIONAL_EXPRESSIVE, "Emotional/Expressive", "Expressive language focusing on emotions and feelings"),
            (DescriptorProfile.CINEMATIC_DRAMATIC, "Cinematic/Dramatic", "Dramatic, cinematic descriptions with visual impact"),
            (DescriptorProfile.TECHNICAL_MECHANICAL, "Technical/Mechanical", "Technical descriptions focusing on function and mechanics")
        ]

        for i, (profile_type, name, description) in enumerate(profiles):
            radio = QRadioButton(name)
            radio.setToolTip(description)
            if i == 0:  # Default selection
                radio.setChecked(True)
            self.profile_buttons.addButton(radio, i)
            profile_layout.addWidget(radio)

        layout.addWidget(profile_group)

        # Descriptiveness controls
        descriptiveness_group = QGroupBox("Descriptiveness Levels")
        desc_layout = QVBoxLayout(descriptiveness_group)

        # Overall descriptiveness
        self.overall_slider = DescriptivenessSlider("Overall Detail Level")
        desc_layout.addWidget(self.overall_slider)

        # Spatial descriptiveness
        self.spatial_slider = DescriptivenessSlider("Spatial Relationships")
        desc_layout.addWidget(self.spatial_slider)

        # Movement descriptiveness
        self.movement_slider = DescriptivenessSlider("Movement & Animation")
        desc_layout.addWidget(self.movement_slider)

        # Style descriptiveness
        self.style_slider = DescriptivenessSlider("Style & Appearance")
        desc_layout.addWidget(self.style_slider)
        self.style_slider.add_shadow_effect() # Example of applying the shadow

        layout.addWidget(descriptiveness_group)

        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout(advanced_group)

        # Style override
        self.style_override = QLineEdit()
        self.style_override.setPlaceholderText("Custom style keywords (optional)")
        advanced_layout.addRow("Style Override:", self.style_override)

        # Focus areas
        self.focus_areas = QLineEdit()
        self.focus_areas.setPlaceholderText("Specific focus areas (e.g., 'face, hands, expression')")
        advanced_layout.addRow("Focus Areas:", self.focus_areas)

        layout.addWidget(advanced_group)

        # Connect signals
        self.profile_buttons.idClicked.connect(self._on_profile_changed)
        self.overall_slider.value_changed.connect(self._on_descriptiveness_changed)
        self.spatial_slider.value_changed.connect(self._on_descriptiveness_changed)
        self.movement_slider.value_changed.connect(self._on_descriptiveness_changed)
        self.style_slider.value_changed.connect(self._on_descriptiveness_changed)
        self.style_override.textChanged.connect(self._on_text_changed)
        self.focus_areas.textChanged.connect(self._on_text_changed)

    def _on_profile_changed(self, button_id: int):
        """Handle profile selection change"""
        profiles = [
            DescriptorProfile.ANATOMICAL_PRECISE,
            DescriptorProfile.MATERIAL_STRUCTURAL,
            DescriptorProfile.ATMOSPHERIC_MELLOW,
            DescriptorProfile.EMOTIONAL_EXPRESSIVE,
            DescriptorProfile.CINEMATIC_DRAMATIC,
            DescriptorProfile.TECHNICAL_MECHANICAL
        ]

        self.current_profile.profile = profiles[button_id]
        self._emit_profile_changed()

    def _on_descriptiveness_changed(self):
        """Handle descriptiveness slider changes"""
        self.current_profile.overall_descriptiveness = self.overall_slider.get_value()
        self.current_profile.spatial_descriptiveness = self.spatial_slider.get_value()
        self.current_profile.movement_descriptiveness = self.movement_slider.get_value()
        self.current_profile.style_descriptiveness = self.style_slider.get_value()
        self._emit_profile_changed()

    def _on_text_changed(self):
        """Handle text field changes"""
        self.current_profile.style_override = self.style_override.text()
        self.current_profile.focus_areas = self.focus_areas.text().split(',') if self.focus_areas.text() else []
        self._emit_profile_changed()

    def _emit_profile_changed(self):
        """Emit profile changed signal"""
        self.profile_changed.emit(self.current_profile)

    def set_profile(self, profile: AIProfile):
        """Set the current AI profile"""
        self.current_profile = profile

        # Update UI elements
        profiles = [
            DescriptorProfile.ANATOMICAL_PRECISE,
            DescriptorProfile.MATERIAL_STRUCTURAL,
            DescriptorProfile.ATMOSPHERIC_MELLOW,
            DescriptorProfile.EMOTIONAL_EXPRESSIVE,
            DescriptorProfile.CINEMATIC_DRAMATIC,
            DescriptorProfile.TECHNICAL_MECHANICAL
        ]

        try:
            index = profiles.index(profile)
            self.profile_buttons.button(index).setChecked(True)
        except ValueError:
            pass

        # Update sliders
        self.overall_slider.set_value(profile.overall_descriptiveness)
        self.spatial_slider.set_value(profile.spatial_descriptiveness)
        self.movement_slider.set_value(profile.movement_descriptiveness)
        self.style_slider.set_value(profile.style_descriptiveness)

        # Update text fields
        self.style_override.setText(profile.style_override or "")
        self.focus_areas.setText(", ".join(profile.focus_areas or []))


class PropertiesPanel(QWidget):
    """Main properties panel for editing selected visual tags"""

    tag_updated = pyqtSignal(str, dict)  # tag_id, updates
    keyframe_set = pyqtSignal(str, str, float, object)  # tag_id, property, time, value

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.theme_manager = framework.get_service("theme_manager")

        self.scene: Scene = None
        self.selected_tag: VisualTag = None
        self.current_time = 0.0

        self._init_ui()
        self._apply_modern_styling()

    def _init_ui(self):
        """Initialize the properties panel UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Header
        header = QLabel("🔧 Tag Properties")
        header.setFont(QFont("", 14, QFont.Weight.Bold))
        main_layout.addWidget(header)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(4, 4, 4, 4)

        # Basic properties group
        self.basic_group = QGroupBox("Basic Properties")
        basic_layout = QFormLayout(self.basic_group)

        # Name
        self.name_edit = QLineEdit()
        basic_layout.addRow("Name:", self.name_edit)

        # Element type
        self.type_combo = QComboBox()
        self.type_combo.addItems([et.value.title() for et in ElementType])
        basic_layout.addRow("Type:", self.type_combo)

        # Visibility
        self.visible_checkbox = QCheckBox("Visible")
        self.visible_checkbox.setChecked(True)
        basic_layout.addRow("", self.visible_checkbox)

        content_layout.addWidget(self.basic_group)

        # Transform properties group
        self.transform_group = QGroupBox("Transform")
        transform_layout = QFormLayout(self.transform_group)

        # Position controls
        position_layout = QHBoxLayout()
        self.pos_x_spin = QDoubleSpinBox()
        self.pos_x_spin.setRange(-9999, 9999)
        self.pos_x_spin.setDecimals(1)
        self.pos_y_spin = QDoubleSpinBox()
        self.pos_y_spin.setRange(-9999, 9999)
        self.pos_y_spin.setDecimals(1)
        self.pos_z_spin = QDoubleSpinBox()
        self.pos_z_spin.setRange(-9999, 9999)
        self.pos_z_spin.setDecimals(1)

        position_layout.addWidget(QLabel("X:"))
        position_layout.addWidget(self.pos_x_spin)
        position_layout.addWidget(QLabel("Y:"))
        position_layout.addWidget(self.pos_y_spin)
        position_layout.addWidget(QLabel("Z:"))
        position_layout.addWidget(self.pos_z_spin)

        # Set keyframe button for position
        self.pos_keyframe_btn = QPushButton("🔑")
        self.pos_keyframe_btn.setFixedSize(24, 24)
        self.pos_keyframe_btn.setToolTip("Set position keyframe")
        position_layout.addWidget(self.pos_keyframe_btn)

        transform_layout.addRow("Position:", position_layout)

        # Scale controls
        scale_layout = QHBoxLayout()
        self.scale_x_spin = QDoubleSpinBox()
        self.scale_x_spin.setRange(0.01, 100.0)
        self.scale_x_spin.setValue(1.0)
        self.scale_x_spin.setDecimals(2)
        self.scale_y_spin = QDoubleSpinBox()
        self.scale_y_spin.setRange(0.01, 100.0)
        self.scale_y_spin.setValue(1.0)
        self.scale_y_spin.setDecimals(2)
        self.scale_z_spin = QDoubleSpinBox()
        self.scale_z_spin.setRange(0.01, 100.0)
        self.scale_z_spin.setValue(1.0)
        self.scale_z_spin.setDecimals(2)

        scale_layout.addWidget(QLabel("X:"))
        scale_layout.addWidget(self.scale_x_spin)
        scale_layout.addWidget(QLabel("Y:"))
        scale_layout.addWidget(self.scale_y_spin)
        scale_layout.addWidget(QLabel("Z:"))
        scale_layout.addWidget(self.scale_z_spin)

        # Set keyframe button for scale
        self.scale_keyframe_btn = QPushButton("🔑")
        self.scale_keyframe_btn.setFixedSize(24, 24)
        self.scale_keyframe_btn.setToolTip("Set scale keyframe")
        scale_layout.addWidget(self.scale_keyframe_btn)

        transform_layout.addRow("Scale:", scale_layout)

        # Opacity
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setSuffix("%")

        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_spin)

        # Set keyframe button for opacity
        self.opacity_keyframe_btn = QPushButton("🔑")
        self.opacity_keyframe_btn.setFixedSize(24, 24)
        self.opacity_keyframe_btn.setToolTip("Set opacity keyframe")
        opacity_layout.addWidget(self.opacity_keyframe_btn)

        transform_layout.addRow("Opacity:", opacity_layout)

        content_layout.addWidget(self.transform_group)

        # AI Profile editor
        self.ai_profile_editor = AIProfileEditor()
        content_layout.addWidget(self.ai_profile_editor)

        # Custom properties group
        self.custom_group = QGroupBox("Custom Properties")
        custom_layout = QVBoxLayout(self.custom_group)

        self.custom_text = QTextEdit()
        self.custom_text.setMaximumHeight(100)
        self.custom_text.setPlaceholderText("Additional custom properties or notes...")
        custom_layout.addWidget(self.custom_text)

        content_layout.addWidget(self.custom_group)

        content_layout.addStretch()

        # No selection placeholder
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.addStretch()

        placeholder_label = QLabel("No tag selected\n\nSelect a visual tag from the canvas\nto edit its properties")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: #6c757d; font-style: italic; padding: 20px;")
        placeholder_layout.addWidget(placeholder_label)
        placeholder_layout.addStretch()

        # Stack widgets
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.placeholder_widget)

        # Initially show placeholder
        scroll_area.setVisible(False)
        self.placeholder_widget.setVisible(True)

        self._connect_signals()

    def _connect_signals(self):
        """Connect property panel signals"""
        # Basic properties
        self.name_edit.textChanged.connect(self._on_property_changed)
        self.type_combo.currentTextChanged.connect(self._on_property_changed)
        self.visible_checkbox.toggled.connect(self._on_property_changed)

        # Transform properties
        self.pos_x_spin.valueChanged.connect(self._on_transform_changed)
        self.pos_y_spin.valueChanged.connect(self._on_transform_changed)
        self.pos_z_spin.valueChanged.connect(self._on_transform_changed)
        self.scale_x_spin.valueChanged.connect(self._on_transform_changed)
        self.scale_y_spin.valueChanged.connect(self._on_transform_changed)
        self.scale_z_spin.valueChanged.connect(self._on_transform_changed)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_spin.valueChanged.connect(self._on_opacity_changed)

        # Keyframe buttons
        self.pos_keyframe_btn.clicked.connect(self._set_position_keyframe)
        self.scale_keyframe_btn.clicked.connect(self._set_scale_keyframe)
        self.opacity_keyframe_btn.clicked.connect(self._set_opacity_keyframe)

        # AI Profile
        self.ai_profile_editor.profile_changed.connect(self._on_ai_profile_changed)

        # Custom properties
        self.custom_text.textChanged.connect(self._on_property_changed)

    def _apply_modern_styling(self):
        """Apply modern styling to the properties panel"""
        if self.theme_manager:
            apply_modern_style(self, self.theme_manager, "card")

    def set_scene(self, scene: Scene):
        """Set the current scene"""
        self.scene = scene

    def set_current_time(self, time: float):
        """Set the current timeline position"""
        self.current_time = time

    def set_selected_tag(self, tag: VisualTag):
        """Set the currently selected tag"""
        self.selected_tag = tag

        if tag:
            self._update_ui_from_tag()
            self.children()[1].setVisible(True)  # scroll_area
            self.placeholder_widget.setVisible(False)
        else:
            self.children()[1].setVisible(False)  # scroll_area
            self.placeholder_widget.setVisible(True)

    def _update_ui_from_tag(self):
        """Update UI controls from selected tag"""
        if not self.selected_tag:
            return

        # Block signals during update
        self._block_signals(True)

        try:
            # Basic properties
            self.name_edit.setText(self.selected_tag.name or "")
            self.type_combo.setCurrentText(self.selected_tag.element_type.value.title())
            self.visible_checkbox.setChecked(self.selected_tag.visible)

            # Transform properties
            self.pos_x_spin.setValue(self.selected_tag.transform.position.x)
            self.pos_y_spin.setValue(self.selected_tag.transform.position.y)
            self.pos_z_spin.setValue(self.selected_tag.transform.position.z)
            self.scale_x_spin.setValue(self.selected_tag.transform.scale.x)
            self.scale_y_spin.setValue(self.selected_tag.transform.scale.y)
            self.scale_z_spin.setValue(self.selected_tag.transform.scale.z)

            opacity = int(self.selected_tag.opacity * 100)
            self.opacity_slider.setValue(opacity)
            self.opacity_spin.setValue(opacity)

            # AI Profile
            if self.selected_tag.primary_profile:
                self.ai_profile_editor.set_profile(self.selected_tag.primary_profile)

            # Custom properties
            custom_text = self.selected_tag.properties.get("custom_description", "")
            self.custom_text.setPlainText(str(custom_text))

        finally:
            self._block_signals(False)

    def _block_signals(self, block: bool):
        """Block/unblock all widget signals"""
        widgets = [
            self.name_edit, self.type_combo, self.visible_checkbox,
            self.pos_x_spin, self.pos_y_spin, self.pos_z_spin,
            self.scale_x_spin, self.scale_y_spin, self.scale_z_spin,
            self.opacity_slider, self.opacity_spin, self.custom_text
        ]

        for widget in widgets:
            widget.blockSignals(block)

    def _on_property_changed(self):
        """Handle basic property changes"""
        if not self.selected_tag:
            return

        updates = {}

        # Name
        if self.selected_tag.name != self.name_edit.text():
            updates["name"] = self.name_edit.text()

        # Element type
        new_type = ElementType(self.type_combo.currentText().lower())
        if self.selected_tag.element_type != new_type:
            updates["element_type"] = new_type

        # Visibility
        if self.selected_tag.visible != self.visible_checkbox.isChecked():
            updates["visible"] = self.visible_checkbox.isChecked()

        # Custom properties
        custom_text = self.custom_text.toPlainText()
        if self.selected_tag.properties.get("custom_description", "") != custom_text:
            updates["properties"] = {"custom_description": custom_text}

        if updates:
            self.tag_updated.emit(self.selected_tag.id, updates)

    def _on_transform_changed(self):
        """Handle transform property changes"""
        if not self.selected_tag:
            return

        # Update tag transform
        self.selected_tag.transform.position.x = self.pos_x_spin.value()
        self.selected_tag.transform.position.y = self.pos_y_spin.value()
        self.selected_tag.transform.position.z = self.pos_z_spin.value()
        self.selected_tag.transform.scale.x = self.scale_x_spin.value()
        self.selected_tag.transform.scale.y = self.scale_y_spin.value()
        self.selected_tag.transform.scale.z = self.scale_z_spin.value()

        # Emit update
        self.tag_updated.emit(self.selected_tag.id, {"transform": self.selected_tag.transform})

    def _on_opacity_changed(self):
        """Handle opacity changes"""
        if not self.selected_tag:
            return

        # Keep slider and spinbox in sync
        sender = self.sender()
        if sender == self.opacity_slider:
            self.opacity_spin.setValue(self.opacity_slider.value())
        else:
            self.opacity_slider.setValue(self.opacity_spin.value())

        # Update tag opacity
        opacity = self.opacity_slider.value() / 100.0
        self.selected_tag.opacity = opacity

        # Emit update
        self.tag_updated.emit(self.selected_tag.id, {"opacity": opacity})

    def _on_ai_profile_changed(self, profile: AIProfile):
        """Handle AI profile changes"""
        if not self.selected_tag:
            return

        self.selected_tag.primary_profile = profile
        self.tag_updated.emit(self.selected_tag.id, {"primary_profile": profile})

    def _set_position_keyframe(self):
        """Set position keyframe at current time"""
        if not self.selected_tag:
            return

        position = self.selected_tag.transform.position
        self.keyframe_set.emit(self.selected_tag.id, "position.x", self.current_time, position.x)
        self.keyframe_set.emit(self.selected_tag.id, "position.y", self.current_time, position.y)
        self.keyframe_set.emit(self.selected_tag.id, "position.z", self.current_time, position.z)

    def _set_scale_keyframe(self):
        """Set scale keyframe at current time"""
        if not self.selected_tag:
            return

        scale = self.selected_tag.transform.scale
        self.keyframe_set.emit(self.selected_tag.id, "scale.x", self.current_time, scale.x)
        self.keyframe_set.emit(self.selected_tag.id, "scale.y", self.current_time, scale.y)
        self.keyframe_set.emit(self.selected_tag.id, "scale.z", self.current_time, scale.z)

    def _set_opacity_keyframe(self):
        """Set opacity keyframe at current time"""
        if not self.selected_tag:
            return

        self.keyframe_set.emit(self.selected_tag.id, "opacity", self.current_time, self.selected_tag.opacity)