from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ThemeType(Enum):
    LIGHT = "light"
    DARK = "dark"
    BLUE = "blue"
    PROFESSIONAL = "professional"
    HIGH_CONTRAST = "high_contrast"

@dataclass
class ThemeColors:
    """Color scheme for a theme"""
    # Background colors
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_hover: str
    bg_selected: str
    bg_pressed: str

    # Text colors
    text_primary: str
    text_secondary: str
    text_disabled: str
    text_accent: str

    # Border colors
    border_light: str
    border_normal: str
    border_dark: str
    border_focus: str

    # Accent colors
    accent_primary: str
    accent_secondary: str
    accent_success: str
    accent_warning: str
    accent_error: str

    # Status colors
    status_info: str
    status_success: str
    status_warning: str
    status_error: str

class ThemeManager:
    """
    Manages application themes and provides consistent styling across all components
    """

    def __init__(self, framework):
        self.framework = framework
        self.settings = framework.get_service("settings_service")
        self.current_theme = ThemeType.LIGHT
        self.themes = self._create_default_themes()
        self._load_theme_from_settings()

    def _create_default_themes(self) -> Dict[ThemeType, ThemeColors]:
        """Create all default theme color schemes"""
        return {
            ThemeType.LIGHT: ThemeColors(
                # Light theme - clean and modern
                bg_primary="#ffffff",
                bg_secondary="#f8f9fa",
                bg_tertiary="#e9ecef",
                bg_hover="#e3f2fd",
                bg_selected="#2196f3",
                bg_pressed="#bbdefb",

                text_primary="#212529",
                text_secondary="#6c757d",
                text_disabled="#adb5bd",
                text_accent="#1976d2",

                border_light="#f1f3f4",
                border_normal="#dee2e6",
                border_dark="#adb5bd",
                border_focus="#90caf9",

                accent_primary="#2196f3",
                accent_secondary="#1976d2",
                accent_success="#4caf50",
                accent_warning="#ff9800",
                accent_error="#f44336",

                status_info="#2196f3",
                status_success="#4caf50",
                status_warning="#ff9800",
                status_error="#f44336"
            ),

            ThemeType.DARK: ThemeColors(
                # Dark theme - easy on the eyes
                bg_primary="#1a1a1a",
                bg_secondary="#2d2d2d",
                bg_tertiary="#404040",
                bg_hover="#3d5afe",
                bg_selected="#3f51b5",
                bg_pressed="#303f9f",

                text_primary="#ffffff",
                text_secondary="#b0b0b0",
                text_disabled="#666666",
                text_accent="#64b5f6",

                border_light="#333333",
                border_normal="#555555",
                border_dark="#777777",
                border_focus="#64b5f6",

                accent_primary="#3f51b5",
                accent_secondary="#303f9f",
                accent_success="#66bb6a",
                accent_warning="#ffa726",
                accent_error="#ef5350",

                status_info="#42a5f5",
                status_success="#66bb6a",
                status_warning="#ffa726",
                status_error="#ef5350"
            ),

            ThemeType.BLUE: ThemeColors(
                # Blue professional theme
                bg_primary="#f3f7fb",
                bg_secondary="#e3f2fd",
                bg_tertiary="#bbdefb",
                bg_hover="#90caf9",
                bg_selected="#1976d2",
                bg_pressed="#1565c0",

                text_primary="#0d47a1",
                text_secondary="#1565c0",
                text_disabled="#90a4ae",
                text_accent="#0277bd",

                border_light="#e1f5fe",
                border_normal="#b3e5fc",
                border_dark="#4fc3f7",
                border_focus="#29b6f6",

                accent_primary="#1976d2",
                accent_secondary="#1565c0",
                accent_success="#2e7d32",
                accent_warning="#f57c00",
                accent_error="#c62828",

                status_info="#0288d1",
                status_success="#388e3c",
                status_warning="#f57c00",
                status_error="#d32f2f"
            ),

            ThemeType.PROFESSIONAL: ThemeColors(
                # Professional gray theme
                bg_primary="#fafafa",
                bg_secondary="#f0f0f0",
                bg_tertiary="#e0e0e0",
                bg_hover="#eeeeee",
                bg_selected="#616161",
                bg_pressed="#757575",

                text_primary="#212121",
                text_secondary="#424242",
                text_disabled="#9e9e9e",
                text_accent="#37474f",

                border_light="#f5f5f5",
                border_normal="#e0e0e0",
                border_dark="#bdbdbd",
                border_focus="#607d8b",

                accent_primary="#546e7a",
                accent_secondary="#37474f",
                accent_success="#2e7d32",
                accent_warning="#ef6c00",
                accent_error="#c62828",

                status_info="#546e7a",
                status_success="#388e3c",
                status_warning="#f57c00",
                status_error="#d32f2f"
            ),

            ThemeType.HIGH_CONTRAST: ThemeColors(
                # High contrast for accessibility
                bg_primary="#ffffff",
                bg_secondary="#f0f0f0",
                bg_tertiary="#e0e0e0",
                bg_hover="#000080",
                bg_selected="#000080",
                bg_pressed="#000060",

                text_primary="#000000",
                text_secondary="#333333",
                text_disabled="#666666",
                text_accent="#000080",

                border_light="#cccccc",
                border_normal="#808080",
                border_dark="#404040",
                border_focus="#000080",

                accent_primary="#000080",
                accent_secondary="#000060",
                accent_success="#008000",
                accent_warning="#ff8000",
                accent_error="#ff0000",

                status_info="#000080",
                status_success="#008000",
                status_warning="#ff8000",
                status_error="#ff0000"
            )
        }

    def get_current_theme(self) -> ThemeColors:
        """Get the currently active theme colors"""
        return self.themes[self.current_theme]

    def set_theme(self, theme_type: ThemeType):
        """Change the active theme"""
        if theme_type in self.themes:
            self.current_theme = theme_type
            if self.settings:
                self.settings.set("ui_theme", theme_type.value)
            self._apply_theme()

    def get_theme_names(self) -> Dict[ThemeType, str]:
        """Get user-friendly theme names"""
        return {
            ThemeType.LIGHT: "Light Theme",
            ThemeType.DARK: "Dark Theme",
            ThemeType.BLUE: "Blue Professional",
            ThemeType.PROFESSIONAL: "Professional Gray",
            ThemeType.HIGH_CONTRAST: "High Contrast"
        }

    def get_stylesheet(self, component_type: str = "default") -> str:
        """Generate CSS stylesheet for different component types"""
        colors = self.get_current_theme()

        if component_type == "header":
            return self._generate_header_stylesheet(colors)
        elif component_type == "button":
            return self._generate_button_stylesheet(colors)
        elif component_type == "menu":
            return self._generate_menu_stylesheet(colors)
        elif component_type == "tree":
            return self._generate_tree_stylesheet(colors)
        elif component_type == "list":
            return self._generate_list_stylesheet(colors)
        elif component_type == "dialog":
            return self._generate_dialog_stylesheet(colors)
        else:
            return self._generate_default_stylesheet(colors)

    def _generate_header_stylesheet(self, colors: ThemeColors) -> str:
        """Generate stylesheet for header components"""
        return f"""
            QWidget {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {colors.bg_secondary}, stop: 1 {colors.bg_tertiary});
                border-bottom: 1px solid {colors.border_normal};
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px 8px;
                font-weight: 500;
                font-size: 13px;
                min-width: 24px;
                min-height: 24px;
                color: {colors.text_primary};
            }}
            QToolButton:hover {{
                background: {colors.bg_hover};
                border-color: {colors.border_focus};
            }}
            QToolButton:pressed {{
                background: {colors.bg_pressed};
            }}
            QToolButton:checked {{
                background: {colors.bg_selected};
                color: {colors.text_primary if self.current_theme != ThemeType.LIGHT else "#ffffff"};
                border-color: {colors.accent_secondary};
            }}
            QLabel {{
                color: {colors.text_primary};
                font-weight: 600;
            }}
        """

    def _generate_button_stylesheet(self, colors: ThemeColors) -> str:
        """Generate stylesheet for buttons"""
        return f"""
            QPushButton {{
                background: {colors.bg_primary};
                border: 1px solid {colors.border_normal};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                color: {colors.text_primary};
                min-height: 20px;
            }}
            QPushButton:hover {{
                background: {colors.bg_hover};
                border-color: {colors.border_focus};
            }}
            QPushButton:pressed {{
                background: {colors.bg_pressed};
            }}
            QPushButton:default {{
                background: {colors.accent_primary};
                color: {colors.text_primary if self.current_theme != ThemeType.LIGHT else "#ffffff"};
                border-color: {colors.accent_secondary};
            }}
            QPushButton:default:hover {{
                background: {colors.accent_secondary};
            }}
        """

    def _generate_menu_stylesheet(self, colors: ThemeColors) -> str:
        """Generate stylesheet for menus"""
        return f"""
            QMenu {{
                background-color: {colors.bg_primary};
                border: 1px solid {colors.border_normal};
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                color: {colors.text_primary};
            }}
            QMenu::item {{
                padding: 6px 12px;
                border-radius: 4px;
                color: {colors.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {colors.bg_hover};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {colors.border_normal};
                margin: 4px 0;
            }}
        """

    def _generate_tree_stylesheet(self, colors: ThemeColors) -> str:
        """Generate stylesheet for tree views"""
        return f"""
            QTreeView {{
                background-color: {colors.bg_secondary};
                border: 1px solid {colors.border_normal};
                border-radius: 4px;
                font-size: 13px;
                color: {colors.text_primary};
                show-decoration-selected: 1;
            }}
            QTreeView::item {{
                height: 24px;
                border: none;
                padding: 2px 8px;
            }}
            QTreeView::item:hover {{
                background-color: {colors.bg_hover};
            }}
            QTreeView::item:selected {{
                background-color: {colors.bg_selected};
                color: {colors.text_primary if self.current_theme != ThemeType.LIGHT else "#ffffff"};
            }}
        """

    def _generate_list_stylesheet(self, colors: ThemeColors) -> str:
        """Generate stylesheet for list views"""
        return f"""
            QListView {{
                background-color: {colors.bg_primary};
                border: 1px solid {colors.border_normal};
                border-radius: 4px;
                font-size: 13px;
                color: {colors.text_primary};
            }}
            QListView::item {{
                padding: 4px;
                border-radius: 4px;
            }}
            QListView::item:hover {{
                background-color: {colors.bg_hover};
            }}
            QListView::item:selected {{
                background-color: {colors.bg_selected};
                color: {colors.text_primary if self.current_theme != ThemeType.LIGHT else "#ffffff"};
            }}
        """

    def _generate_dialog_stylesheet(self, colors: ThemeColors) -> str:
        """Generate stylesheet for dialogs"""
        return f"""
            QDialog {{
                background-color: {colors.bg_primary};
                color: {colors.text_primary};
            }}
            QGroupBox {{
                font-weight: 600;
                border: 1px solid {colors.border_normal};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                color: {colors.text_primary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: {colors.text_accent};
            }}
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {colors.bg_primary};
                border: 1px solid {colors.border_normal};
                border-radius: 4px;
                padding: 6px;
                font-size: 13px;
                color: {colors.text_primary};
            }}
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border-color: {colors.border_focus};
            }}
        """

    def _generate_default_stylesheet(self, colors: ThemeColors) -> str:
        """Generate default stylesheet"""
        return f"""
            * {{
                color: {colors.text_primary};
                background-color: {colors.bg_primary};
            }}
        """

    def _load_theme_from_settings(self):
        """Load theme preference from settings"""
        if self.settings:
            theme_value = self.settings.get("ui_theme", "light")
            try:
                self.current_theme = ThemeType(theme_value)
            except ValueError:
                self.current_theme = ThemeType.LIGHT

    def _apply_theme(self):
        """Apply the current theme to all UI components"""
        # This would trigger a UI refresh event
        if hasattr(self.framework, 'get_service'):
            event_manager = self.framework.get_service("event_manager")
            if event_manager:
                event_manager.publish("ui:theme_changed", theme=self.current_theme)