# plugins/assets/ui/package_editor_widget.py
import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QToolButton,
    QSplitter, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QInputDialog, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal


class RuleEditorDialog(QDialog):
    """A dialog for creating and editing a scan rule."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Scan Rule")
        layout = QFormLayout(self)
        self.condition_type = QComboBox()
        self.condition_type.addItems(["if_filename_contains", "if_folder_is", "if_analyzer_tag_is"])
        self.operator = QComboBox()
        self.operator.addItems(["CONTAINS", "IS", "DOES_NOT_CONTAIN"])
        self.value_edit = QLineEdit()
        layout.addRow("Condition:", self.condition_type)
        layout.addRow("Operator:", self.operator)
        layout.addRow("Value:", self.value_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_rule(self):
        return {
            "condition": self.condition_type.currentText(),
            "operator": self.operator.currentText(),
            "value": self.value_edit.text()
        }


class PackageEditorWidget(QWidget):
    """A widget for editing the metadata and rules of an asset package."""
    package_saved = pyqtSignal()

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.commands = framework.get_service("command_manager")
        self._current_manifest_path = None
        self._manifest_data = {}
        self._is_loading = False
        self._init_ui()
        self._connect_signals()
        self.load_package(None)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        self.package_name_label = QLabel("<h2>No Package Loaded</h2>")
        header_layout.addWidget(self.package_name_label, 1)
        self.save_button = QToolButton(text="💾 Save Changes")
        header_layout.addWidget(self.save_button)
        self.scan_button = QToolButton(text="🔍 Scan Package Assets")
        header_layout.addWidget(self.scan_button)
        main_layout.addLayout(header_layout)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        intents_widget = QWidget()
        intents_layout = QVBoxLayout(intents_widget)
        intents_layout.addWidget(QLabel("<b>Categories / Intents</b>"))
        self.intents_list = QListWidget()
        intents_layout.addWidget(self.intents_list)
        intents_buttons_layout = QHBoxLayout()
        self.add_intent_button = QToolButton(text="➕ Add")
        self.remove_intent_button = QToolButton(text="➖ Remove")
        intents_buttons_layout.addStretch()
        intents_buttons_layout.addWidget(self.add_intent_button)
        intents_buttons_layout.addWidget(self.remove_intent_button)
        intents_layout.addLayout(intents_buttons_layout)
        rules_widget = QWidget()
        rules_layout = QVBoxLayout(rules_widget)
        rules_layout.addWidget(QLabel("<b>Smart Scan Rules for Selected Category</b>"))
        self.rules_table = QTableWidget(0, 3)
        self.rules_table.setHorizontalHeaderLabels(["Condition Type", "Operator", "Value"])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        rules_layout.addWidget(self.rules_table)
        rules_buttons_layout = QHBoxLayout()
        self.add_rule_button = QToolButton(text="➕ Add Rule")
        self.remove_rule_button = QToolButton(text="➖ Remove Rule")
        rules_buttons_layout.addStretch()
        rules_buttons_layout.addWidget(self.add_rule_button)
        rules_buttons_layout.addWidget(self.remove_rule_button)
        rules_layout.addLayout(rules_buttons_layout)
        content_splitter.addWidget(intents_widget)
        content_splitter.addWidget(rules_widget)
        main_layout.addWidget(content_splitter, 1)

    def _connect_signals(self):
        self.save_button.clicked.connect(self._save_manifest)
        self.scan_button.clicked.connect(self._scan_package)
        self.add_intent_button.clicked.connect(self._add_intent)
        self.remove_intent_button.clicked.connect(self._remove_intent)
        self.add_rule_button.clicked.connect(self._add_rule)
        self.remove_rule_button.clicked.connect(self._remove_rule)
        self.intents_list.currentItemChanged.connect(self._on_intent_selected)

    def load_package(self, package_data):
        self._is_loading = True
        if not package_data:
            self._current_manifest_path = None
            self._manifest_data = {}
            self.package_name_label.setText("<h2>No Package Selected</h2>")
            self.intents_list.clear()
            self.rules_table.setRowCount(0)
            self.save_button.setEnabled(False)
            self.scan_button.setEnabled(False)
        else:
            self._current_manifest_path = os.path.join(package_data.get('path', ''), "asset.json")
            self.package_name_label.setText(f"<h2>{package_data.get('name', 'N/A')}</h2>")
            self.save_button.setEnabled(True)
            self.scan_button.setEnabled(True)
            try:
                with open(self._current_manifest_path, 'r', encoding='utf-8') as f:
                    self._manifest_data = json.load(f)
                self._populate_intents()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load package manifest:\n{e}")
        self._is_loading = False
        if self.intents_list.count() > 0:
            self.intents_list.setCurrentRow(0)

    def _populate_intents(self):
        self.intents_list.clear()
        for intent_name in sorted(self._manifest_data.get("intents", {}).keys()):
            self.intents_list.addItem(QListWidgetItem(intent_name))

    def _on_intent_selected(self, current, previous=None):
        if self._is_loading or not current:
            self.rules_table.setRowCount(0)
            return
        intent_name = current.text()
        intent_rules = [r for r in self._manifest_data.get("scan_rules", []) if r.get("intent") == intent_name]
        self.rules_table.setRowCount(len(intent_rules))
        for row, rule in enumerate(intent_rules):
            self.rules_table.setItem(row, 0, QTableWidgetItem(rule.get("condition", "")))
            self.rules_table.setItem(row, 1, QTableWidgetItem(rule.get("operator", "")))
            self.rules_table.setItem(row, 2, QTableWidgetItem(str(rule.get("value", ""))))

    def _add_intent(self):
        text, ok = QInputDialog.getText(self, 'Add Category', 'Enter new category name:')
        if ok and text:
            intent_name = text.strip()
            intents = self._manifest_data.setdefault("intents", {})
            intents[intent_name] = {"paths": [], "weight": 1.0}
            self._populate_intents()

    def _remove_intent(self):
        current = self.intents_list.currentItem()
        if not current: return
        intent_name = current.text()
        if QMessageBox.question(self, "Remove", f"Remove '{intent_name}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self._manifest_data.get("intents", {}).pop(intent_name, None)
            self._manifest_data["scan_rules"] = [r for r in self._manifest_data.get("scan_rules", []) if
                                                 r.get("intent") != intent_name]
            self._populate_intents()

    def _add_rule(self):
        current = self.intents_list.currentItem()
        if not current: return
        dialog = RuleEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rule = dialog.get_rule()
            rule["intent"] = current.text()
            self._manifest_data.setdefault("scan_rules", []).append(rule)
            self._on_intent_selected(current)

    def _remove_rule(self):
        current_intent = self.intents_list.currentItem()
        current_rule_row = self.rules_table.currentRow()
        if not current_intent or current_rule_row < 0: return

        intent_name = current_intent.text()
        all_rules = self._manifest_data.get("scan_rules", [])
        intent_rules_indices = [i for i, r in enumerate(all_rules) if r.get("intent") == intent_name]

        if current_rule_row < len(intent_rules_indices):
            rule_to_remove_index = intent_rules_indices[current_rule_row]
            del all_rules[rule_to_remove_index]
            self._on_intent_selected(current_intent)

    def _save_manifest(self):
        if not self._current_manifest_path: return
        try:
            with open(self._current_manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self._manifest_data, f, indent=2)
            self.log.notification(f"Saved: {os.path.basename(self._current_manifest_path)}")
            self.package_saved.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save manifest:\n{e}")

    def _scan_package(self):
        uuid = self._manifest_data.get("uuid")
        if uuid:
            self.commands.execute("assets.resync_emotion_packages", package_uuid=uuid)
