# story_studio_project/plugins/shell/main_window.py
import os
from PyQt6.QtWidgets import ( QMainWindow, QStatusBar, QDockWidget, QLabel, QToolBar,
    QComboBox )
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QAction

# --- Global Stylesheet ---
APP_STYLESHEET = """
    /* General window styling */
    QMainWindow, QDockWidget {
        background-color: #3c3c3c;
        color: #f0f0f0;
    }
    QDockWidget::title {
        background-color: #4a4a4a;
        padding: 4px;
        border-radius: 4px;
    }

    /* Rounded corners for input widgets */
    QLineEdit, QTextEdit, QComboBox, QListView, QTreeView, QFrame {
        border: 1px solid #555;
        border-radius: 4px;
        padding: 2px;
        background-color: #2c2c2c;
    }

    /* Style for buttons */
    QPushButton, QToolButton {
        background-color: #5a5a5a;
        border: 1px solid #666;
        border-radius: 4px;
        padding: 5px;
    }
    QPushButton:hover, QToolButton:hover {
        background-color: #6a6a6a;
    }
    QPushButton:pressed, QToolButton:pressed {
        background-color: #4a4a4a;
    }

    /* Style for list view items to have rounded corners */
    QListView::item {
        border-radius: 6px;
        margin: 2px;
    }

    /* Tab styling */
    QTabWidget::pane { border-top: 2px solid #555; }
    QTabBar::tab {
        background: #444;
        border: 1px solid #555;
        border-bottom-color: #3c3c3c;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        min-width: 8ex;
        padding: 5px;
    }
    QTabBar::tab:selected { background: #5a5a5a; }
"""


class MainWindow(QMainWindow):
    """The main application window (shell) that hosts all other UI components."""

    def __init__(self, framework, app):
        super().__init__()
        self.framework = framework
        self.app = app
        self.log = framework.get_service("log_manager")
        self.settings = framework.get_service("settings_service")
        self.docks = {}

        self.setWindowTitle("Interactive Generative Story Studio")
        self.app.setStyleSheet(APP_STYLESHEET)
        self.setStatusBar(QStatusBar(self))
        self.log.subscribe_to_notifications(self.statusBar().showMessage)
        self._create_settings_toolbar()

        geometry_hex = self.settings.get("window_geometry")
        if geometry_hex:
            self.restoreGeometry(QByteArray.fromHex(geometry_hex.encode()))

    def _create_settings_toolbar(self):
        settings_toolbar = QToolBar("Settings")
        settings_toolbar.setObjectName("settings_toolbar")
        settings_toolbar.addWidget(QLabel(" Log Level: "))
        log_level_combo = QComboBox()
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        log_level_combo.addItems(log_levels)
        saved_level = self.settings.get("log_level", "INFO").upper()
        if saved_level in log_levels:
            log_level_combo.setCurrentText(saved_level)
            self.log.set_level(saved_level)
        log_level_combo.currentTextChanged.connect(self._on_log_level_changed)
        settings_toolbar.addWidget(log_level_combo)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, settings_toolbar)

    def _on_log_level_changed(self, level_name):
        self.log.set_level(level_name)
        self.settings.set("log_level", level_name)

    def build_from_contributions(self):
        self.log.info("Shell is building UI from contributions...")
        self._build_central_widget()
        self._build_docks()
        self._build_menus()
        state_hex = self.settings.get("window_state")
        if state_hex:
            self.restoreState(QByteArray.fromHex(state_hex.encode()))

    def _build_central_widget(self):
        contribs = self.framework.get_contributions("ui_central_widget")
        if contribs:
            widget_class = contribs[0].get('class')
            if widget_class:
                self.setCentralWidget(widget_class(self.framework))

    def _build_docks(self):
        for contrib in self.framework.get_contributions("ui_docks"):
            try:
                dock_id = contrib['id']
                content_widget = contrib['class'](self.framework)
                dock = QDockWidget(contrib.get('title', 'Panel'), self)
                dock.setObjectName(dock_id)

                # --- NEW: Check for and set a custom title bar ---
                if hasattr(content_widget, 'get_title_bar_widget'):
                    title_bar = content_widget.get_title_bar_widget()
                    if title_bar:
                        dock.setTitleBarWidget(title_bar)

                dock.setWidget(content_widget)
                area_str = contrib.get('default_area', 'left')
                area = getattr(Qt.DockWidgetArea, f"{area_str.title()}DockWidgetArea", Qt.DockWidgetArea.LeftDockWidgetArea)
                self.addDockWidget(area, dock)
                self.docks[dock_id] = dock

                panel_states = self.settings.get("panel_states", {})
                if dock_id in panel_states and hasattr(content_widget, "restore_state"):
                    content_widget.restore_state(panel_states[dock_id])

            except Exception as e:
                self.log.error(f"Failed to create dock widget '{contrib.get('id')}': {e}", exc_info=True)

    def _build_menus(self):
        self.menuBar().clear()
        if self.docks:
            window_menu = self.menuBar().addMenu("Window")
            for dock in self.docks.values():
                window_menu.addAction(dock.toggleViewAction())

        dev_menu = self.menuBar().addMenu("&Developer")
        reload_action = QAction("Reload Plugins", self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(lambda: self.framework.command_manager.execute("framework.reload_plugins"))
        dev_menu.addAction(reload_action)

    def clear_all_docks(self):
        for dock in self.docks.values():
            self.removeDockWidget(dock)
            dock.deleteLater()
        self.docks.clear()

    def closeEvent(self, event):
        self.settings.set("window_geometry", self.saveGeometry().toHex().data().decode())
        self.settings.set("window_state", self.saveState().toHex().data().decode())
        panel_states = {
            dock_id: dock.widget().save_state()
            for dock_id, dock in self.docks.items()
            if hasattr(dock.widget(), "save_state")
        }
        if panel_states:
            self.settings.set("panel_states", panel_states)
        super().closeEvent(event)
