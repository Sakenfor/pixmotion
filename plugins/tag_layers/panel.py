
from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QHBoxLayout, QComboBox
from PyQt6.QtCore import Qt

class TagLayersPanel(QWidget):
    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.registry = framework.get_service("tag_layer_registry")
        self.scan_profiles = framework.get_service("scan_profile_service")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Tag Layers</b>"))
        self.list = QListWidget(); layout.addWidget(self.list)
        row = QHBoxLayout()
        self.profile = QComboBox(); row.addWidget(self.profile, 1)
        self.run_btn = QPushButton("Run Profile"); row.addWidget(self.run_btn)
        layout.addLayout(row)
        self.run_btn.clicked.connect(self._run_profile)
        self.refresh()

    def refresh(self):
        self.list.clear()
        layers = self.registry.list_layers() if self.registry else {}
        for lid, desc in layers.items():
            self.list.addItem(f"{lid} — {desc.get('name','(no name)')}")
        self.profile.clear()
        profiles = self.scan_profiles.list_profiles() if self.scan_profiles else {}
        for pid, spec in profiles.items():
            self.profile.addItem(spec.get("label", pid), pid)

    def _run_profile(self):
        pid = self.profile.currentData()
        if not pid: return
        self.scan_profiles.run_profile(pid)
