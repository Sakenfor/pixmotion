"""
Qualitative scale picker widget for the graph editor.
Provides an intuitive way to select descriptive values that map to numeric ranges.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSlider, QSpinBox, QPushButton, QGroupBox, QTextEdit,
    QFrame, QFormLayout
)
from PyQt6.QtGui import QFont


class QualitativeScalePicker(QWidget):
    """Widget for selecting qualitative descriptors with visual feedback."""

    valueChanged = pyqtSignal(str, str, float)  # scale_id, descriptor, numeric_value

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.graph_registry = framework.graph_registry if framework else None
        self.current_scale_id: Optional[str] = None
        self.current_descriptor: str = ""
        self.current_value: float = 0.0
        self.scales: Dict[str, Any] = {}
        self.setup_ui()
        self.load_scales()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scale selection
        scale_group = QGroupBox("Qualitative Scale")
        scale_layout = QFormLayout(scale_group)

        self.scale_combo = QComboBox()
        self.scale_combo.currentTextChanged.connect(self.on_scale_changed)
        scale_layout.addRow("Scale:", self.scale_combo)

        layout.addWidget(scale_group)

        # Descriptor selection
        descriptor_group = QGroupBox("Descriptor")
        descriptor_layout = QVBoxLayout(descriptor_group)

        # Descriptor buttons layout (horizontal scrollable)
        self.descriptor_frame = QFrame()
        self.descriptor_layout = QHBoxLayout(self.descriptor_frame)
        self.descriptor_layout.setContentsMargins(5, 5, 5, 5)
        descriptor_layout.addWidget(self.descriptor_frame)

        # Current value display
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Numeric Value:"))
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        value_layout.addWidget(self.value_label)
        value_layout.addStretch()
        descriptor_layout.addLayout(value_layout)

        # Fine-tune slider
        self.fine_tune_slider = QSlider(Qt.Orientation.Horizontal)
        self.fine_tune_slider.setVisible(False)  # Hidden by default
        self.fine_tune_slider.valueChanged.connect(self.on_fine_tune_changed)
        descriptor_layout.addWidget(QLabel("Fine Tune:"))
        descriptor_layout.addWidget(self.fine_tune_slider)

        # Toggle fine tune
        self.fine_tune_button = QPushButton("Fine Tune")
        self.fine_tune_button.setCheckable(True)
        self.fine_tune_button.toggled.connect(self.toggle_fine_tune)
        descriptor_layout.addWidget(self.fine_tune_button)

        layout.addWidget(descriptor_group)

        # Description area
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(60)
        self.description_text.setReadOnly(True)
        self.description_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd;")
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.description_text)

    def load_scales(self):
        """Load available qualitative scales from the graph registry."""
        self.scales.clear()
        self.scale_combo.clear()

        if not self.graph_registry:
            return

        # Get scales from registry
        scales = getattr(self.graph_registry, 'qualitative_scales', {})
        for scale_id, scale_data in scales.items():
            self.scales[scale_id] = scale_data
            label = scale_data.get('label', scale_id)
            self.scale_combo.addItem(label, scale_id)

        # Add default if no scales available
        if not self.scales:
            self._add_default_scales()

    def _add_default_scales(self):
        """Add some default scales for demonstration."""
        from plugins.core.graph_scales import DEFAULT_QUALITATIVE_SCALES

        for scale_data in DEFAULT_QUALITATIVE_SCALES:
            scale_id = scale_data['id']
            self.scales[scale_id] = scale_data
            label = scale_data.get('label', scale_id)
            self.scale_combo.addItem(label, scale_id)

    def on_scale_changed(self, text: str):
        """Handle scale selection change."""
        if not text:
            return

        # Find scale by label
        scale_id = None
        for sid, scale_data in self.scales.items():
            if scale_data.get('label', sid) == text:
                scale_id = sid
                break

        if not scale_id:
            return

        self.current_scale_id = scale_id
        self.update_descriptor_buttons()

        # Select default descriptor
        scale_data = self.scales[scale_id]
        default_descriptor = scale_data.get('default_descriptor', '')
        if default_descriptor:
            self.select_descriptor(default_descriptor)

    def update_descriptor_buttons(self):
        """Update the descriptor selection buttons."""
        # Clear existing buttons
        for i in reversed(range(self.descriptor_layout.count())):
            child = self.descriptor_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        if not self.current_scale_id:
            return

        scale_data = self.scales[self.current_scale_id]
        descriptors = scale_data.get('descriptors', [])

        for desc_data in descriptors:
            name = desc_data['name']
            label = desc_data.get('metadata', {}).get('label', name.replace('_', ' ').title())

            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty('descriptor_name', name)
            button.setProperty('descriptor_data', desc_data)
            button.clicked.connect(lambda checked, n=name: self.select_descriptor(n))

            # Style based on range
            range_values = desc_data.get('range', [0, 100])
            hue = int((range_values[0] + range_values[1]) / 2 * 360 / 100)  # Map to hue
            button.setStyleSheet(f"""
                QPushButton {{
                    border: 2px solid hsl({hue}, 70%, 60%);
                    border-radius: 4px;
                    padding: 6px 12px;
                    margin: 2px;
                    background-color: hsl({hue}, 70%, 95%);
                }}
                QPushButton:checked {{
                    background-color: hsl({hue}, 70%, 60%);
                    color: white;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: hsl({hue}, 70%, 80%);
                }}
            """)

            self.descriptor_layout.addWidget(button)

        self.descriptor_layout.addStretch()

    def select_descriptor(self, descriptor_name: str):
        """Select a descriptor and update the display."""
        if not self.current_scale_id:
            return

        scale_data = self.scales[self.current_scale_id]
        descriptors = scale_data.get('descriptors', [])

        # Find descriptor data
        descriptor_data = None
        for desc in descriptors:
            if desc['name'] == descriptor_name:
                descriptor_data = desc
                break

        if not descriptor_data:
            return

        self.current_descriptor = descriptor_name

        # Update button states
        for i in range(self.descriptor_layout.count()):
            widget = self.descriptor_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setChecked(widget.property('descriptor_name') == descriptor_name)

        # Calculate numeric value (middle of range with jitter)
        range_values = descriptor_data.get('range', [0, 100])
        jitter = descriptor_data.get('jitter', 0)
        base_value = (range_values[0] + range_values[1]) / 2

        # Apply small random jitter for variety
        import random
        if jitter > 0:
            self.current_value = base_value + random.uniform(-jitter/2, jitter/2)
        else:
            self.current_value = base_value

        # Clamp to range
        self.current_value = max(range_values[0], min(range_values[1], self.current_value))

        # Update display
        self.value_label.setText(f"{self.current_value:.1f}")

        # Update description
        description = descriptor_data.get('metadata', {}).get('description', 'No description available.')
        self.description_text.setPlainText(description)

        # Setup fine tune slider
        self.fine_tune_slider.setRange(int(range_values[0] * 10), int(range_values[1] * 10))
        self.fine_tune_slider.setValue(int(self.current_value * 10))

        # Emit change
        self.valueChanged.emit(self.current_scale_id, self.current_descriptor, self.current_value)

    def toggle_fine_tune(self, enabled: bool):
        """Toggle fine tune slider visibility."""
        self.fine_tune_slider.setVisible(enabled)

    def on_fine_tune_changed(self, value: int):
        """Handle fine tune slider changes."""
        self.current_value = value / 10.0
        self.value_label.setText(f"{self.current_value:.1f}")

        if self.current_scale_id and self.current_descriptor:
            self.valueChanged.emit(self.current_scale_id, self.current_descriptor, self.current_value)

    def set_value(self, scale_id: str, descriptor: str, value: Optional[float] = None):
        """Set the current value programmatically."""
        # Find and select scale
        for i in range(self.scale_combo.count()):
            combo_scale_id = self.scale_combo.itemData(i)
            if combo_scale_id == scale_id:
                self.scale_combo.setCurrentIndex(i)
                break

        # Select descriptor
        self.select_descriptor(descriptor)

        # Override value if provided
        if value is not None:
            self.current_value = value
            self.value_label.setText(f"{self.current_value:.1f}")
            self.fine_tune_slider.setValue(int(self.current_value * 10))

    def get_value(self) -> tuple[str, str, float]:
        """Get the current selection."""
        return (self.current_scale_id or "", self.current_descriptor, self.current_value)


class QualitativeScaleDialog(QWidget):
    """Standalone dialog for selecting qualitative scale values."""

    def __init__(self, framework, parent=None, initial_scale=None, initial_descriptor=None, initial_value=None):
        super().__init__(parent)
        self.setWindowTitle("Select Qualitative Value")
        self.setModal(True)
        self.result_data = None

        layout = QVBoxLayout(self)

        # Add the picker widget
        self.picker = QualitativeScalePicker(framework, self)
        layout.addWidget(self.picker)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

        # Set initial values
        if initial_scale and initial_descriptor:
            self.picker.set_value(initial_scale, initial_descriptor, initial_value)

    def accept(self):
        """Accept the dialog and store result."""
        self.result_data = self.picker.get_value()
        self.close()

    def reject(self):
        """Cancel the dialog."""
        self.result_data = None
        self.close()

    def get_result(self):
        """Get the selected result data."""
        return self.result_data