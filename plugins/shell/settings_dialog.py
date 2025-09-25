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
    QTabWidget,
    QVBoxLayout,
    QComboBox,
    QGroupBox,
    QTextEdit,
    QFrame,
)
from PyQt6.QtGui import QFont, QPalette


class SettingsDialog(QDialog):
    """Application settings dialog with multiple tabs."""

    def __init__(self, settings_service, framework, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._settings = settings_service
        self.framework = framework
        self.setWindowTitle("Application Settings")
        self.setModal(True)
        self.resize(550, 450)

        # Basic settings
        self._api_key_edit = QLineEdit()
        self._output_dir_edit = QLineEdit()

        # Theme settings
        self._theme_combo = QComboBox()

        self._populate_initial_values()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("⚙️ Application Settings")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Add tabs
        tabs.addTab(self._create_general_tab(), "🔧 General")
        tabs.addTab(self._create_appearance_tab(), "🎨 Appearance")

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_general_tab(self):
        """Create the general settings tab"""
        tab = QWidget()
        layout = QFormLayout(tab)
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

        return tab

    def _create_appearance_tab(self):
        """Create the appearance/theme settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Theme selection group
        theme_group = QGroupBox("Application Theme")
        theme_layout = QFormLayout(theme_group)

        # Theme dropdown
        self._theme_combo.addItems([
            "Dark Blue (Default)",
            "Light",
            "Dark",
            "High Contrast",
            "Cyberpunk"
        ])
        self._theme_combo.currentTextChanged.connect(self._preview_theme)
        theme_layout.addRow(QLabel("Theme:"), self._theme_combo)

        # Theme preview
        preview_label = QLabel("Preview")
        preview_label.setFont(QFont("", 10, QFont.Weight.Bold))
        theme_layout.addRow(preview_label)

        self.theme_preview = QTextEdit()
        self.theme_preview.setMaximumHeight(100)
        self.theme_preview.setPlainText("This is a preview of how the interface will look with the selected theme.")
        self.theme_preview.setReadOnly(True)
        theme_layout.addWidget(self.theme_preview)

        layout.addWidget(theme_group)
        layout.addStretch()

        return tab

    def _populate_initial_values(self) -> None:
        if not self._settings:
            return

        # Basic settings
        self._api_key_edit.setText(self._settings.get("pixverse_api_key", ""))
        self._output_dir_edit.setText(self._settings.get("output_directory", ""))

        # Theme settings
        current_theme = self._settings.get("ui_theme", "dark_blue")
        theme_map = {
            "dark_blue": "Dark Blue (Default)",
            "light": "Light",
            "dark": "Dark",
            "high_contrast": "High Contrast",
            "cyberpunk": "Cyberpunk"
        }
        display_name = theme_map.get(current_theme, "Dark Blue (Default)")
        index = self._theme_combo.findText(display_name)
        if index >= 0:
            self._theme_combo.setCurrentIndex(index)

        # Apply initial theme to preview
        self._update_theme_preview(current_theme)

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

    def _preview_theme(self, theme_display_name):
        """Preview theme changes in real-time"""
        theme_name = self._get_theme_key_from_display(theme_display_name)
        self._update_theme_preview(theme_name)

    def _get_theme_key_from_display(self, display_name):
        """Convert display name back to theme key"""
        reverse_map = {
            "Dark Blue (Default)": "dark_blue",
            "Light": "light",
            "Dark": "dark",
            "High Contrast": "high_contrast",
            "Cyberpunk": "cyberpunk"
        }
        return reverse_map.get(display_name, "dark_blue")

    def _update_theme_preview(self, theme_key):
        """Update the theme preview area"""
        theme_manager = self.framework.get_service("theme_manager")
        if not theme_manager:
            return

        # Get theme colors
        colors = theme_manager.get_theme(theme_key)

        # Apply theme to preview widget
        preview_style = f"""
        QTextEdit {{
            background-color: {colors['background']};
            color: {colors['text']};
            border: 1px solid {colors['border']};
            selection-background-color: {colors['accent']};
        }}
        """
        self.theme_preview.setStyleSheet(preview_style)

    def _apply_and_accept(self) -> None:
        if not self._settings:
            self.accept()
            return

        # Basic settings
        api_key = self._api_key_edit.text().strip()
        output_dir = self._output_dir_edit.text().strip()

        self._settings.set("pixverse_api_key", api_key)
        if output_dir:
            self._settings.resolve_user_path(output_dir)
            self._settings.set("output_directory", output_dir)
        else:
            self._settings.set("output_directory", "")

        # Theme settings
        theme_display = self._theme_combo.currentText()
        theme_key = self._get_theme_key_from_display(theme_display)
        self._settings.set("ui_theme", theme_key)

        # Apply theme immediately
        theme_manager = self.framework.get_service("theme_manager")
        if theme_manager:
            theme_manager.set_theme(theme_key)
            # Notify other components about theme change
            event_manager = self.framework.get_service("event_manager")
            if event_manager:
                event_manager.publish("theme:changed", theme=theme_key)

        self.accept()
