# D:/My Drive/code/pixmotion/plugins/assets/package_editor.py
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
        self.operator.addItems(["CONTAINS", "IS", "DOES_NOT_CONTAIN"])  # Simplified for now

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
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

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
        intents_layout.setContentsMargins(0, 0, 0, 0)
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
        rules_layout.setContentsMargins(0, 0, 0, 0)
        rules_layout.addWidget(QLabel("<b>Smart Scan Rules for Selected Category</b>"))
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(3)
        self.rules_table.setHorizontalHeaderLabels(["Condition Type", "Operator", "Value"])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rules_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
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
        content_splitter.setSizes([220, 480])

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
            for btn in [self.save_button, self.scan_button, self.add_intent_button, self.remove_intent_button,
                        self.add_rule_button, self.remove_rule_button]:
                btn.setEnabled(False)
            self._is_loading = False
            return

        self._current_manifest_path = os.path.join(package_data.get('path'), "asset.json")
        name = package_data.get('name', 'N/A')
        self.package_name_label.setText(f"<h2>{name}</h2>")

        for btn in [self.save_button, self.scan_button, self.add_intent_button, self.remove_intent_button,
                    self.add_rule_button, self.remove_rule_button]:
            btn.setEnabled(True)

        try:
            with open(self._current_manifest_path, 'r', encoding='utf-8') as f:
                self._manifest_data = json.load(f)
            self._populate_intents()
        except Exception as e:
            self.log.error(f"Failed to load manifest {self._current_manifest_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Could not load package manifest:\n{e}")
            self._manifest_data = {}
            self.intents_list.clear()

        self._is_loading = False
        if self.intents_list.count() > 0:
            self.intents_list.setCurrentRow(0)
        else:
            self._on_intent_selected(None)

    def _populate_intents(self):
        self.intents_list.clear()
        intents = self._manifest_data.get("intents", {})
        for intent_name in sorted(intents.keys()):
            self.intents_list.addItem(QListWidgetItem(intent_name))

    def _on_intent_selected(self, current: QListWidgetItem | None):
        if self._is_loading or not current:
            self.rules_table.clearContents()
            self.rules_table.setRowCount(0)
            return

        intent_name = current.text()
        rules = self._manifest_data.get("scan_rules", [])
        intent_rules = [rule for rule in rules if rule.get("intent") == intent_name]

        self.rules_table.clearContents()
        self.rules_table.setRowCount(len(intent_rules))
        for row, rule in enumerate(intent_rules):
            self.rules_table.setItem(row, 0, QTableWidgetItem(rule.get("condition", "")))
            self.rules_table.setItem(row, 1, QTableWidgetItem(rule.get("operator", "")))
            self.rules_table.setItem(row, 2, QTableWidgetItem(str(rule.get("value", ""))))

    def _add_intent(self):
        text, ok = QInputDialog.getText(self, 'Add Category/Intent', 'Enter new category name:')
        if ok and text:
            intent_name = text.strip().lower().replace(" ", "_")
            if not intent_name: return

            intents = self._manifest_data.setdefault("intents", {})
            if intent_name in intents:
                QMessageBox.warning(self, "Duplicate", "A category with this name already exists.")
                return

            intents[intent_name] = {"paths": [], "weight": 1.0}
            self._populate_intents()
            for i in range(self.intents_list.count()):
                if self.intents_list.item(i).text() == intent_name:
                    self.intents_list.setCurrentRow(i)
                    break

    def _remove_intent(self):
        current_item = self.intents_list.currentItem()
        if not current_item: return

        intent_name = current_item.text()
        reply = QMessageBox.question(self, "Remove Category",
                                     f"Are you sure you want to remove '{intent_name}' and all its rules?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if intent_name in self._manifest_data.get("intents", {}):
                del self._manifest_data["intents"][intent_name]

            # Also remove associated scan rules
            self._manifest_data["scan_rules"] = [rule for rule in self._manifest_data.get("scan_rules", []) if
                                                 rule.get("intent") != intent_name]

            self._populate_intents()

    def _add_rule(self):
        current_intent_item = self.intents_list.currentItem()
        if not current_intent_item:
            QMessageBox.warning(self, "No Category", "Please select a category to add a rule to.")
            return

        dialog = RuleEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_rule = dialog.get_rule()
            new_rule["intent"] = current_intent_item.text()

            rules = self._manifest_data.setdefault("scan_rules", [])
            rules.append(new_rule)
            self._on_intent_selected(current_intent_item)

    def _remove_rule(self):
        current_rule_row = self.rules_table.currentRow()
        current_intent_item = self.intents_list.currentItem()
        if current_rule_row < 0 or not current_intent_item:
            return

        intent_name = current_intent_item.text()

        # This logic is a bit complex because we need to find the Nth rule for this specific intent
        rule_to_remove = None
        intent_rule_index = 0
        all_rules = self._manifest_data.get("scan_rules", [])
        for rule in all_rules:
            if rule.get("intent") == intent_name:
                if intent_rule_index == current_rule_row:
                    rule_to_remove = rule
                    break
                intent_rule_index += 1

        if rule_to_remove:
            all_rules.remove(rule_to_remove)
            self._on_intent_selected(current_intent_item)

    def _save_manifest(self):
        if not self._current_manifest_path: return
        try:
            with open(self._current_manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self._manifest_data, f, indent=2)
            self.log.notification(f"Saved package manifest: {os.path.basename(self._current_manifest_path)}")
            self.package_saved.emit()
        except Exception as e:
            self.log.error(f"Failed to save manifest: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Could not save package manifest:\n{e}")

    def _scan_package(self):
        if not self._manifest_data: return
        uuid = self._manifest_data.get("uuid")
        if uuid:
            self.log.info(f"Triggering smart scan for package: {uuid}")
            self.commands.execute("assets.resync_emotion_packages", package_uuid=uuid)

