# plugins/assets/ui/dialogs.py
from PyQt6.QtWidgets import (
    QDialog,
    QLineEdit,
    QDialogButtonBox,
    QFormLayout,
)

class CreatePackageDialog(QDialog):
    """Dialog to get the name for a new asset package."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Asset Package")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., NPC Greeting Animations")
        layout.addRow("Package Name:", self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_name(self):
        return self.name_edit.text().strip()

