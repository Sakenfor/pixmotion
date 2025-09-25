"""
Advanced node properties editor widget for the graph editor.
Replaces raw JSON editors with structured inputs for better usability.
"""

from __future__ import annotations
import json
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QPushButton, QGroupBox,
    QScrollArea, QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox
)

from framework.graph_schema import GraphNode, NodeAction, ActionVariant


class TagChipsWidget(QWidget):
    """Widget for displaying and editing tags as removable chips."""

    tagsChanged = pyqtSignal(list)  # Emitted when tags are modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Input area for new tags
        input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tag name...")
        self.tag_input.returnPressed.connect(self.add_tag)

        self.add_button = QPushButton("Add Tag")
        self.add_button.clicked.connect(self.add_tag)

        input_layout.addWidget(self.tag_input)
        input_layout.addWidget(self.add_button)
        layout.addLayout(input_layout)

        # Scroll area for tags
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(100)
        self.scroll_area.setMaximumHeight(150)

        self.chips_widget = QWidget()
        self.chips_layout = QVBoxLayout(self.chips_widget)
        self.chips_layout.setContentsMargins(5, 5, 5, 5)

        self.scroll_area.setWidget(self.chips_widget)
        layout.addWidget(self.scroll_area)

    def set_tags(self, tags: List[str]):
        """Set the current tags and update display."""
        self.tags = tags.copy()
        self.update_chips_display()

    def get_tags(self) -> List[str]:
        """Get the current list of tags."""
        return self.tags.copy()

    def add_tag(self):
        """Add a new tag from the input field."""
        tag_text = self.tag_input.text().strip()
        if tag_text and tag_text not in self.tags:
            self.tags.append(tag_text)
            self.tag_input.clear()
            self.update_chips_display()
            self.tagsChanged.emit(self.tags)

    def remove_tag(self, tag: str):
        """Remove a tag from the list."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_chips_display()
            self.tagsChanged.emit(self.tags)

    def update_chips_display(self):
        """Update the visual display of tag chips."""
        # Clear existing chips
        for i in reversed(range(self.chips_layout.count())):
            child = self.chips_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Create new chips
        if not self.tags:
            label = QLabel("No tags")
            label.setStyleSheet("color: gray; font-style: italic;")
            self.chips_layout.addWidget(label)
        else:
            for tag in self.tags:
                chip = self.create_tag_chip(tag)
                self.chips_layout.addWidget(chip)

        # Add stretch to push chips to top
        self.chips_layout.addStretch()

    def create_tag_chip(self, tag: str) -> QWidget:
        """Create a visual chip widget for a tag."""
        chip = QFrame()
        chip.setFrameStyle(QFrame.Shape.StyledPanel)
        chip.setStyleSheet("""
            QFrame {
                background-color: #2196F3;
                color: white;
                border-radius: 12px;
                padding: 4px 8px;
                margin: 2px;
            }
        """)

        layout = QHBoxLayout(chip)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        label = QLabel(tag)
        label.setStyleSheet("background: transparent; color: white;")

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.3);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.5);
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_tag(tag))

        layout.addWidget(label)
        layout.addWidget(remove_btn)

        return chip


class KeyValueTableWidget(QWidget):
    """Widget for editing key-value pairs in a table format."""

    dataChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Property")
        self.add_button.clicked.connect(self.add_row)
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected)

        btn_layout.addWidget(self.add_button)
        btn_layout.addWidget(self.remove_button)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.itemChanged.connect(self.on_item_changed)

        layout.addWidget(self.table)

    def set_data(self, data: Dict[str, Any]):
        """Set the key-value data."""
        self.table.setRowCount(len(data))
        for row, (key, value) in enumerate(data.items()):
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))

    def get_data(self) -> Dict[str, Any]:
        """Get the current key-value data."""
        data = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)

            if key_item and key_item.text().strip():
                key = key_item.text().strip()
                value = value_item.text() if value_item else ""

                # Try to parse as JSON for complex values
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string

                data[key] = value

        return data

    def add_row(self):
        """Add a new empty row."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.editItem(self.table.item(row, 0))

    def remove_selected(self):
        """Remove selected rows."""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)

        self.on_item_changed()

    def on_item_changed(self):
        """Handle table item changes."""
        self.dataChanged.emit(self.get_data())


class NodeActionsEditor(QWidget):
    """Advanced editor for node actions with visual interface."""

    actionsChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.actions = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header with add button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Actions:"))
        header_layout.addStretch()

        self.add_action_btn = QPushButton("Add Action")
        self.add_action_btn.clicked.connect(self.add_action)
        header_layout.addWidget(self.add_action_btn)
        layout.addLayout(header_layout)

        # Scroll area for actions
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)

        self.actions_widget = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_widget)
        self.actions_layout.setContentsMargins(5, 5, 5, 5)

        self.scroll_area.setWidget(self.actions_widget)
        layout.addWidget(self.scroll_area)

    def set_actions(self, actions: List[NodeAction]):
        """Set the current actions."""
        self.actions = [action for action in actions]  # Copy
        self.update_actions_display()

    def get_actions(self) -> List[NodeAction]:
        """Get the current actions."""
        return self.actions.copy()

    def add_action(self):
        """Add a new action."""
        new_action = NodeAction(
            id=f"action_{len(self.actions) + 1}",
            mode="one_shot"
        )
        self.actions.append(new_action)
        self.update_actions_display()
        self.actionsChanged.emit(self.actions)

    def remove_action(self, index: int):
        """Remove an action by index."""
        if 0 <= index < len(self.actions):
            del self.actions[index]
            self.update_actions_display()
            self.actionsChanged.emit(self.actions)

    def update_actions_display(self):
        """Update the visual display of actions."""
        # Clear existing widgets
        for i in reversed(range(self.actions_layout.count())):
            child = self.actions_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        if not self.actions:
            label = QLabel("No actions defined")
            label.setStyleSheet("color: gray; font-style: italic;")
            self.actions_layout.addWidget(label)
        else:
            for i, action in enumerate(self.actions):
                action_widget = self.create_action_widget(action, i)
                self.actions_layout.addWidget(action_widget)

        self.actions_layout.addStretch()

    def create_action_widget(self, action: NodeAction, index: int) -> QWidget:
        """Create a widget for editing a single action."""
        group = QGroupBox(f"Action: {action.id}")
        layout = QFormLayout(group)

        # Basic properties
        id_edit = QLineEdit(action.id)
        id_edit.textChanged.connect(lambda text: setattr(action, 'id', text))
        layout.addRow("ID:", id_edit)

        mode_combo = QComboBox()
        mode_combo.addItems(["one_shot", "loop", "sequence", "playlist"])
        mode_combo.setCurrentText(action.mode)
        mode_combo.currentTextChanged.connect(lambda text: setattr(action, 'mode', text))
        layout.addRow("Mode:", mode_combo)

        priority_spin = QDoubleSpinBox()
        priority_spin.setRange(-999.0, 999.0)
        priority_spin.setValue(action.priority)
        priority_spin.valueChanged.connect(lambda val: setattr(action, 'priority', val))
        layout.addRow("Priority:", priority_spin)

        cooldown_edit = QLineEdit(action.cooldown or "")
        cooldown_edit.textChanged.connect(lambda text: setattr(action, 'cooldown', text if text else None))
        layout.addRow("Cooldown:", cooldown_edit)

        # Remove button
        remove_btn = QPushButton("Remove Action")
        remove_btn.clicked.connect(lambda: self.remove_action(index))
        remove_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        layout.addRow(remove_btn)

        return group


class NodePropertiesWidget(QWidget):
    """Advanced node properties editor with structured inputs."""

    nodeChanged = pyqtSignal(object)  # Emits the modified GraphNode

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_node = None
        self.setup_ui()

    def setup_ui(self):
        # Main scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        # Content widget
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        # Basic properties
        basic_group = QGroupBox("Basic Properties")
        basic_layout = QFormLayout(basic_group)

        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)  # ID shouldn't be editable in properties
        basic_layout.addRow("ID:", self.id_edit)

        self.type_edit = QLineEdit()
        self.type_edit.textChanged.connect(self.on_property_changed)
        basic_layout.addRow("Type:", self.type_edit)

        self.label_edit = QLineEdit()
        self.label_edit.textChanged.connect(self.on_property_changed)
        basic_layout.addRow("Label:", self.label_edit)

        layout.addWidget(basic_group)

        # Tags
        tags_group = QGroupBox("Tags")
        tags_layout = QVBoxLayout(tags_group)
        self.tags_widget = TagChipsWidget()
        self.tags_widget.tagsChanged.connect(self.on_property_changed)
        tags_layout.addWidget(self.tags_widget)
        layout.addWidget(tags_group)

        # Asset References
        assets_group = QGroupBox("Asset References")
        assets_layout = QVBoxLayout(assets_group)
        self.asset_refs_widget = TagChipsWidget()  # Reuse for asset IDs
        self.asset_refs_widget.tagsChanged.connect(self.on_property_changed)
        assets_layout.addWidget(self.asset_refs_widget)
        layout.addWidget(assets_group)

        # Properties (key-value pairs)
        props_group = QGroupBox("Properties")
        props_layout = QVBoxLayout(props_group)
        self.properties_widget = KeyValueTableWidget()
        self.properties_widget.dataChanged.connect(self.on_property_changed)
        props_layout.addWidget(self.properties_widget)
        layout.addWidget(props_group)

        # Metadata (key-value pairs)
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QVBoxLayout(metadata_group)
        self.metadata_widget = KeyValueTableWidget()
        self.metadata_widget.dataChanged.connect(self.on_property_changed)
        metadata_layout.addWidget(self.metadata_widget)
        layout.addWidget(metadata_group)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        self.actions_widget = NodeActionsEditor()
        self.actions_widget.actionsChanged.connect(self.on_property_changed)
        actions_layout.addWidget(self.actions_widget)
        layout.addWidget(actions_group)

        layout.addStretch()

    def set_node(self, node: Optional[GraphNode]):
        """Set the node to edit."""
        self.current_node = node
        if node:
            self.id_edit.setText(node.id)
            self.type_edit.setText(node.type)
            self.label_edit.setText(node.label or "")
            self.tags_widget.set_tags(node.tags)
            self.asset_refs_widget.set_tags(node.asset_refs)
            self.properties_widget.set_data(node.properties)
            self.metadata_widget.set_data(node.metadata)
            self.actions_widget.set_actions(node.actions)
        else:
            self.clear_form()

    def clear_form(self):
        """Clear all form fields."""
        self.id_edit.clear()
        self.type_edit.clear()
        self.label_edit.clear()
        self.tags_widget.set_tags([])
        self.asset_refs_widget.set_tags([])
        self.properties_widget.set_data({})
        self.metadata_widget.set_data({})
        self.actions_widget.set_actions([])

    def on_property_changed(self):
        """Handle property changes and update the node."""
        if not self.current_node:
            return

        # Update node properties
        self.current_node.type = self.type_edit.text()
        self.current_node.label = self.label_edit.text()
        self.current_node.tags = self.tags_widget.get_tags()
        self.current_node.asset_refs = self.asset_refs_widget.get_tags()
        self.current_node.properties = self.properties_widget.get_data()
        self.current_node.metadata = self.metadata_widget.get_data()
        self.current_node.actions = self.actions_widget.get_actions()

        # Emit change signal
        self.nodeChanged.emit(self.current_node)