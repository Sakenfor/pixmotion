# story_studio_project/run_app.py
import sys
from PyQt6.QtWidgets import QApplication
from framework import Framework

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Apply a global stylesheet for rounded corners
    stylesheet = """
        QFrame, QPushButton, QLineEdit, QTextEdit, QComboBox, QListView, QTreeView {
            border-radius: 6px;
        }
    """
    app.setStyleSheet(stylesheet)

    # The Framework class is the central hub of the application.
    # It initializes all core services.
    framework = Framework()

    # The initialize method loads all plugins and then shows the main UI shell.
    framework.initialize(app)
