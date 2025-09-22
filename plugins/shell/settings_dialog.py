from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QWidget,
)


class SettingsDialog(QDialog):
    """Simple dialog for editing core application settings."""

    def __init__(self, settings_service, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._settings = settings_service
        self.setWindowTitle("Application Settings")
        self.setModal(True)
        self.resize(420, 180)

        self._api_key_edit = QLineEdit()
        self._output_dir_edit = QLineEdit()

        self._populate_initial_values()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        layout.addRow(QLabel("Pixverse API Key"), self._api_key_edit)

        output_row = QHBoxLayout()
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.setSpacing(6)
        output_row.addWidget(self._output_dir_edit, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_for_output_dir)
        output_row.addWidget(browse_btn)
        layout.addRow(QLabel("Output Directory"), output_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _populate_initial_values(self) -> None:
        if not self._settings:
            return
        self._api_key_edit.setText(self._settings.get("pixverse_api_key", ""))
        self._output_dir_edit.setText(self._settings.get("output_directory", ""))

    # ------------------------------------------------------------------
    # Slots

    def _browse_for_output_dir(self) -> None:
        current = self._output_dir_edit.text() or os.getcwd()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            current,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )
        if directory:
            self._output_dir_edit.setText(directory)

    def _apply_and_accept(self) -> None:
        if not self._settings:
            self.accept()
            return

        api_key = self._api_key_edit.text().strip()
        output_dir = self._output_dir_edit.text().strip()

        self._settings.set("pixverse_api_key", api_key)
        if output_dir:
            self._settings.resolve_user_path(output_dir)
            self._settings.set("output_directory", output_dir)
        else:
            self._settings.set("output_directory", "")

        self.accept()
