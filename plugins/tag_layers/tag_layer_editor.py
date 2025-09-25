import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QToolButton,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox,
    QFormLayout, QComboBox, QTextEdit, QCheckBox
)
from PyQt6.QtCore import Qt
from framework.modern_ui import ModernCard, ModernSplitter, apply_modern_style


class TagLayerEditorPanel(QWidget):
    def __init__(self, framework):
        super().__init__()
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.registry = framework.get_service("tag_layer_registry")
        self.theme_manager = framework.get_service("theme_manager")
        self._is_loading = False
        self._init_ui()
        self._connect_signals()
        self.load_layers()
        self._apply_modern_theme()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = ModernSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("<b>Tag Layers</b>"))
        self.layers_list = QListWidget()
        left_layout.addWidget(self.layers_list)
        list_buttons_layout = QHBoxLayout()
        self.add_layer_button = QToolButton(text="➕ Add")
        self.remove_layer_button = QToolButton(text="➖ Remove")
        list_buttons_layout.addStretch()
        list_buttons_layout.addWidget(self.add_layer_button)
        list_buttons_layout.addWidget(self.remove_layer_button)
        left_layout.addLayout(list_buttons_layout)

        right_widget = QWidget()
        form_layout = QFormLayout(right_widget)
        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.stage_combo = QComboBox();
        self.stage_combo.addItems(["quick", "deep", "manual"])
        self.value_type_combo = QComboBox();
        self.value_type_combo.addItems(["categorical", "numeric", "text", "embedding"])
        self.multi_select_check = QCheckBox("Allow multiple tags per asset")
        self.engine_edit = QTextEdit();
        self.engine_edit.setPlaceholderText("JSON config for AI Hub...")
        self.hierarchy_edit = QTextEdit();
        self.hierarchy_edit.setPlaceholderText("JSON for tag hierarchy...")
        self.save_button = QToolButton(text="💾 Save Changes")

        form_layout.addRow("ID:", self.id_edit)
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Stage:", self.stage_combo)
        form_layout.addRow("Value Type:", self.value_type_combo)
        form_layout.addRow("", self.multi_select_check)
        form_layout.addRow(QLabel("<b>Engine Config (JSON)</b>"))
        form_layout.addRow(self.engine_edit)
        form_layout.addRow(QLabel("<b>Hierarchy (JSON)</b>"))
        form_layout.addRow(self.hierarchy_edit)
        form_layout.addRow("", self.save_button)

        splitter.addWidget(left_widget);
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 400])
        main_layout.addWidget(splitter)

    def _connect_signals(self):
        self.layers_list.currentItemChanged.connect(self._on_layer_selected)
        self.add_layer_button.clicked.connect(self._add_layer)
        self.remove_layer_button.clicked.connect(self._remove_layer)
        self.save_button.clicked.connect(self._save_layer)

    def load_layers(self):
        self._is_loading = True
        self.layers_list.clear()
        for layer in sorted(self.registry.list_layers(), key=lambda l: l['id']):
            item = QListWidgetItem(f"{layer['name']} [{layer['id']}]")
            item.setData(Qt.ItemDataRole.UserRole, layer['id'])
            self.layers_list.addItem(item)
        self._is_loading = False
        if self.layers_list.count() > 0:
            self.layers_list.setCurrentRow(0)
        else:
            self._clear_form()

    def _on_layer_selected(self, current, previous):
        if self._is_loading or not current:
            self._clear_form()
            return
        layer_data = self.registry.get_layer(current.data(Qt.ItemDataRole.UserRole))
        if layer_data: self._populate_form(layer_data)

    def _populate_form(self, data: dict):
        self.id_edit.setText(data.get("id", ""));
        self.id_edit.setReadOnly(True)
        self.name_edit.setText(data.get("name", ""))
        self.description_edit.setPlainText(data.get("description", ""))
        self.stage_combo.setCurrentText(data.get("stage", "quick"))
        self.value_type_combo.setCurrentText(data.get("value_type", "categorical"))
        self.multi_select_check.setChecked(data.get("multi_select", True))
        self.engine_edit.setPlainText(json.dumps(data.get("engine", {}), indent=2))
        self.hierarchy_edit.setPlainText(json.dumps(data.get("hierarchy", {}), indent=2))
        self.save_button.setEnabled(True)

    def _clear_form(self):
        self.id_edit.clear();
        self.id_edit.setReadOnly(False)
        self.name_edit.clear();
        self.description_edit.clear()
        self.stage_combo.setCurrentIndex(0);
        self.value_type_combo.setCurrentIndex(0)
        self.multi_select_check.setChecked(True)
        self.engine_edit.clear();
        self.hierarchy_edit.clear()
        self.save_button.setEnabled(True)

    def _add_layer(self):
        self.layers_list.clearSelection()
        self._clear_form()
        self.id_edit.setFocus()

    def _remove_layer(self):
        current_item = self.layers_list.currentItem()
        if not current_item: return
        layer_id = current_item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Remove Layer", f"Delete '{layer_id}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.registry.delete_layer(layer_id)
            self.load_layers()

    def _save_layer(self):
        layer_id = self.id_edit.text().strip()
        if not layer_id:
            QMessageBox.warning(self, "Validation Error", "ID is required.")
            return
        try:
            engine = json.loads(self.engine_edit.toPlainText() or "{}")
            hierarchy = json.loads(self.hierarchy_edit.toPlainText() or "{}")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON Error", f"Invalid JSON: {e}")
            return

        layer_data = {"id": layer_id, "name": self.name_edit.text().strip(),
                      "description": self.description_edit.toPlainText().strip(),
                      "stage": self.stage_combo.currentText(), "value_type": self.value_type_combo.currentText(),
                      "multi_select": self.multi_select_check.isChecked(), "engine": engine, "hierarchy": hierarchy}
        self.registry.upsert_layer(layer_data)
        self.load_layers()

    def _apply_modern_theme(self):
        """Apply modern theme styling to all UI components"""
        if not self.theme_manager:
            return

        # Apply modern list styling to layers list
        if hasattr(self, 'layers_list'):
            apply_modern_style(self.layers_list, self.theme_manager, "modern_list")

        # Apply modern button styling
        for btn_name in ['add_layer_button', 'remove_layer_button']:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                apply_modern_style(btn, self.theme_manager, "button_secondary")

        # Apply modern input styling to form controls
        for widget_name in ['id_edit', 'name_edit', 'description_edit', 'stage_combo',
                           'value_type_combo', 'engine_edit', 'hierarchy_edit']:
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                apply_modern_style(widget, self.theme_manager, "input")
