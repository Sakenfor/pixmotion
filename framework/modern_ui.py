"""
Modern UI Component Library for PixMotion

Provides modern, theme-aware styling components that integrate with the existing theme system.
Features glass morphism, smooth animations, and contemporary design patterns.
"""

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QToolButton, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton, QSlider,
    QProgressBar, QTabWidget, QTabBar, QGroupBox, QScrollArea, QListView,
    QTreeView, QTableView, QSplitter, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty, QTimer
from PyQt6.QtGui import QFont, QPainter, QBrush, QPen, QColor, QPalette
from typing import Optional, Dict, Any

class ModernUIStyle:
    """
    Modern UI styling that integrates with the existing theme system.
    Provides glass morphism, smooth transitions, and contemporary design patterns.
    """

    @staticmethod
    def get_modern_stylesheet(theme_colors, component_type: str = "default") -> str:
        """Generate modern CSS stylesheets for different component types"""

        if component_type == "card":
            return ModernUIStyle._get_card_style(theme_colors)
        elif component_type == "button_primary":
            return ModernUIStyle._get_primary_button_style(theme_colors)
        elif component_type == "button_secondary":
            return ModernUIStyle._get_secondary_button_style(theme_colors)
        elif component_type == "input":
            return ModernUIStyle._get_input_style(theme_colors)
        elif component_type == "header":
            return ModernUIStyle._get_header_style(theme_colors)
        elif component_type == "sidebar":
            return ModernUIStyle._get_sidebar_style(theme_colors)
        elif component_type == "tab":
            return ModernUIStyle._get_tab_style(theme_colors)
        elif component_type == "glass_panel":
            return ModernUIStyle._get_glass_panel_style(theme_colors)
        elif component_type == "modern_list":
            return ModernUIStyle._get_modern_list_style(theme_colors)
        elif component_type == "floating_toolbar":
            return ModernUIStyle._get_floating_toolbar_style(theme_colors)
        else:
            return ModernUIStyle._get_base_modern_style(theme_colors)

    @staticmethod
    def _get_base_modern_style(colors) -> str:
        """Base modern styling for all components"""
        return f"""
            * {{
                font-family: "Segoe UI", "San Francisco", "Helvetica Neue", Arial, sans-serif;
                font-size: 13px;
                border: none;
                outline: none;
            }}

            QWidget {{
                background-color: {colors.bg_primary};
                color: {colors.text_primary};
            }}

            QFrame {{
                border: 1px solid {colors.border_light};
                border-radius: 8px;
                background: {colors.bg_primary};
            }}
        """

    @staticmethod
    def _get_card_style(colors) -> str:
        """Modern card component styling"""
        return f"""
            QFrame {{
                background: {colors.bg_primary};
                border: 1px solid {colors.border_light};
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            }}
            QFrame:hover {{
                border-color: {colors.border_focus};
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            }}
        """

    @staticmethod
    def _get_primary_button_style(colors) -> str:
        """Modern primary button styling"""
        return f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {colors.accent_primary}, stop: 1 {colors.accent_secondary});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {colors.accent_secondary}, stop: 1 {colors.accent_primary});
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background: {colors.accent_secondary};
                transform: translateY(0px);
            }}
            QPushButton:disabled {{
                background: {colors.bg_tertiary};
                color: {colors.text_disabled};
            }}
        """

    @staticmethod
    def _get_secondary_button_style(colors) -> str:
        """Modern secondary button styling"""
        return f"""
            QPushButton {{
                background: {colors.bg_secondary};
                color: {colors.text_primary};
                border: 1px solid {colors.border_normal};
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 500;
                font-size: 14px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background: {colors.bg_hover};
                border-color: {colors.border_focus};
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background: {colors.bg_pressed};
                transform: translateY(0px);
            }}
        """

    @staticmethod
    def _get_input_style(colors) -> str:
        """Modern input field styling"""
        return f"""
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
                background: {colors.bg_secondary};
                border: 1px solid {colors.border_light};
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                color: {colors.text_primary};
                selection-background-color: {colors.accent_primary};
            }}
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {colors.accent_primary};
                background: {colors.bg_primary};
                box-shadow: 0 0 0 3px {colors.accent_primary}33;
            }}
            QLineEdit:hover, QTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
                border-color: {colors.border_normal};
            }}
        """

    @staticmethod
    def _get_header_style(colors) -> str:
        """Modern header styling"""
        return f"""
            QWidget {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {colors.bg_primary}, stop: 1 {colors.bg_secondary});
                border-bottom: 1px solid {colors.border_light};
                padding: 16px;
            }}
            QLabel {{
                font-size: 18px;
                font-weight: 700;
                color: {colors.text_primary};
                margin: 0;
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 8px 12px;
                margin: 4px;
                font-weight: 500;
                color: {colors.text_primary};
            }}
            QToolButton:hover {{
                background: {colors.bg_hover};
                border-color: {colors.border_focus};
            }}
            QToolButton:checked {{
                background: {colors.accent_primary};
                color: white;
            }}
        """

    @staticmethod
    def _get_sidebar_style(colors) -> str:
        """Modern sidebar styling"""
        return f"""
            QWidget {{
                background: {colors.bg_secondary};
                border-right: 1px solid {colors.border_light};
            }}
            QTreeView, QListView {{
                background: transparent;
                border: none;
                font-size: 14px;
                padding: 8px;
            }}
            QTreeView::item, QListView::item {{
                padding: 8px 12px;
                margin: 2px;
                border-radius: 6px;
                color: {colors.text_primary};
            }}
            QTreeView::item:hover, QListView::item:hover {{
                background: {colors.bg_hover};
            }}
            QTreeView::item:selected, QListView::item:selected {{
                background: {colors.accent_primary};
                color: white;
            }}
        """

    @staticmethod
    def _get_tab_style(colors) -> str:
        """Modern tab styling"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {colors.border_light};
                border-radius: 8px;
                background: {colors.bg_primary};
                margin-top: -1px;
            }}
            QTabBar::tab {{
                background: {colors.bg_secondary};
                border: 1px solid {colors.border_light};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 12px 20px;
                margin-right: 2px;
                font-weight: 500;
                color: {colors.text_secondary};
            }}
            QTabBar::tab:selected {{
                background: {colors.bg_primary};
                color: {colors.text_primary};
                border-color: {colors.accent_primary};
                border-bottom: 2px solid {colors.accent_primary};
            }}
            QTabBar::tab:hover {{
                background: {colors.bg_hover};
                color: {colors.text_primary};
            }}
        """

    @staticmethod
    def _get_glass_panel_style(colors) -> str:
        """Glass morphism panel styling"""
        return f"""
            QFrame {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {colors.bg_primary}E6, stop: 1 {colors.bg_secondary}CC);
                border: 1px solid {colors.border_light}80;
                border-radius: 16px;
                backdrop-filter: blur(10px);
            }}
        """

    @staticmethod
    def _get_modern_list_style(colors) -> str:
        """Modern list view styling"""
        return f"""
            QListView, QTreeView, QTableView {{
                background: {colors.bg_primary};
                border: 1px solid {colors.border_light};
                border-radius: 8px;
                font-size: 14px;
                gridline-color: {colors.border_light};
                selection-background-color: {colors.accent_primary};
            }}
            QListView::item, QTreeView::item, QTableView::item {{
                padding: 12px;
                border-bottom: 1px solid {colors.border_light};
                color: {colors.text_primary};
            }}
            QListView::item:hover, QTreeView::item:hover, QTableView::item:hover {{
                background: {colors.bg_hover};
                border-radius: 6px;
            }}
            QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {{
                background: {colors.accent_primary};
                color: white;
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background: {colors.bg_secondary};
                padding: 8px 12px;
                border: none;
                border-bottom: 1px solid {colors.border_normal};
                font-weight: 600;
                color: {colors.text_primary};
            }}
        """

    @staticmethod
    def _get_floating_toolbar_style(colors) -> str:
        """Floating toolbar styling"""
        return f"""
            QWidget {{
                background: {colors.bg_primary}F0;
                border: 1px solid {colors.border_light};
                border-radius: 12px;
                padding: 8px;
                backdrop-filter: blur(10px);
            }}
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
                color: {colors.text_primary};
            }}
            QToolButton:hover {{
                background: {colors.bg_hover};
            }}
            QToolButton:checked {{
                background: {colors.accent_primary};
                color: white;
            }}
        """


class AnimatedWidget(QWidget):
    """Base class for widgets with smooth animations"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_animations()

    def _setup_animations(self):
        """Setup fade and slide animations"""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def fade_in(self):
        """Smooth fade in animation"""
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def fade_out(self):
        """Smooth fade out animation"""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()


class ModernCard(QFrame):
    """Modern card component with hover effects"""

    def __init__(self, title: str = "", content: QWidget = None, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self._setup_card(title, content)

    def _setup_card(self, title: str, content: QWidget):
        """Setup card layout and styling"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        if title:
            title_label = QLabel(title)
            title_label.setFont(QFont("", 16, QFont.Weight.Bold))
            layout.addWidget(title_label)

        if content:
            layout.addWidget(content)


class ModernButton(QPushButton):
    """Modern button with hover animations"""

    def __init__(self, text: str = "", style: str = "primary", parent=None):
        super().__init__(text, parent)
        self.button_style = style
        self._setup_button()

    def _setup_button(self):
        """Setup button styling and animations"""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Animations would be handled by the theme system


class ModernToolbar(QWidget):
    """Modern floating toolbar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self._setup_toolbar()

    def _setup_toolbar(self):
        """Setup toolbar layout"""
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(4)

    def add_button(self, icon_name: str, tooltip: str, callback=None) -> QToolButton:
        """Add a button to the toolbar"""
        button = QToolButton()
        button.setToolTip(tooltip)
        button.setFixedSize(32, 32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        if callback:
            button.clicked.connect(callback)

        self.layout.addWidget(button)
        return button


class ModernTabWidget(QTabWidget):
    """Modern tab widget with improved styling"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_tabs()

    def _setup_tabs(self):
        """Setup modern tab styling"""
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setMovable(True)
        self.setTabsClosable(False)


class ModernSplitter(QSplitter):
    """Modern splitter with thin handle"""

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setHandleWidth(1)
        self.setChildrenCollapsible(False)


def apply_modern_style(widget: QWidget, theme_manager, style_type: str = "default"):
    """Apply modern styling to any widget"""
    if not theme_manager:
        return

    colors = theme_manager.get_current_theme()
    stylesheet = ModernUIStyle.get_modern_stylesheet(colors, style_type)
    widget.setStyleSheet(stylesheet)