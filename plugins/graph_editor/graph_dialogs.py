from __future__ import annotations

from typing import List, Tuple
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
    QMessageBox,
)
from framework.graph_schema import GraphEdge


class GraphCreateDialog(QDialog):
    def __init__(self, parent, existing_ids: set[str]):
        super().__init__(parent)
        self.setWindowTitle("New Graph")
        self._existing = existing_ids
        self._graph_id = ""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Graph name:"))
        self._name = QLineEdit()
        self._name.textChanged.connect(self._update_id)
        layout.addWidget(self._name)
        layout.addWidget(QLabel("Generated ID:"))
        self._id_label = QLabel("")
        layout.addWidget(self._id_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_id("")

    def _update_id(self, text: str) -> None:
        import re
        base = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower() or "graph"
        cand = base
        i = 1
        while cand in self._existing:
            i += 1
            cand = f"{base}-{i}"
        self._graph_id = cand
        self._id_label.setText(cand)

    def result(self) -> Tuple[str, str]:
        return self._graph_id, self._name.text().strip()


class NodeCreateDialog(QDialog):
    def __init__(self, parent, type_choices: List[str], existing_ids: set[str]):
        super().__init__(parent)
        self.setWindowTitle("Add Node")
        self._existing = existing_ids
        self._node_id = ""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Node type:"))
        self._type = QComboBox()
        self._type.addItems(type_choices or ["generic"])
        layout.addWidget(self._type)
        layout.addWidget(QLabel("Display label:"))
        self._label = QLineEdit()
        self._label.textChanged.connect(self._update_id)
        layout.addWidget(self._label)
        layout.addWidget(QLabel("Generated ID:"))
        self._id_label = QLabel("")
        layout.addWidget(self._id_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_id("")

    def _update_id(self, text: str) -> None:
        import re
        base_source = text or self._type.currentText()
        base = re.sub(r"[^a-zA-Z0-9]+", "-", base_source.strip()).strip("-").lower() or "node"
        cand = base
        i = 1
        while cand in self._existing:
            i += 1
            cand = f"{base}-{i}"
        self._node_id = cand
        self._id_label.setText(cand)

    def result(self) -> Tuple[str, str, str]:
        return self._node_id, self._type.currentText(), self._label.text().strip()


class EdgeCreateDialog(QDialog):
    def __init__(self, parent, node_ids: List[str]):
        super().__init__(parent)
        self.setWindowTitle("Add Edge")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Source node:"))
        self._src = QComboBox()
        self._src.addItems(node_ids)
        layout.addWidget(self._src)
        layout.addWidget(QLabel("Target node:"))
        self._dst = QComboBox()
        self._dst.addItems(node_ids)
        layout.addWidget(self._dst)
        layout.addWidget(QLabel("Relation type:"))
        self._rel = QLineEdit("link")
        layout.addWidget(self._rel)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self):
        if self._src.currentText() == self._dst.currentText():
            QMessageBox.warning(self, "Add Edge", "Source and target must be different.")
            return
        if not self._rel.text().strip():
            QMessageBox.warning(self, "Add Edge", "Relation type cannot be empty.")
            return
        self.accept()

    def result(self) -> Tuple[str, str, str]:
        return self._src.currentText(), self._dst.currentText(), self._rel.text().strip()


class EdgeManageDialog(QDialog):
    def __init__(self, parent, edges: List[GraphEdge]):
        super().__init__(parent)
        self.setWindowTitle("Edit Edge")
        self._edges = edges
        self._mode = "update"
        self._idx = 0
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select edge:"))
        self._edge_combo = QComboBox()
        for e in edges:
            self._edge_combo.addItem(f"{e.source} -> {e.target} ({e.relation_type})")
        self._edge_combo.currentIndexChanged.connect(self._sync)
        layout.addWidget(self._edge_combo)
        layout.addWidget(QLabel("Relation type:"))
        self._rel = QLineEdit()
        layout.addWidget(self._rel)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._delete_btn = buttons.addButton("Delete", QDialogButtonBox.ButtonRole.DestructiveRole)
        buttons.accepted.connect(self._accept_update)
        buttons.rejected.connect(self.reject)
        self._delete_btn.clicked.connect(self._accept_delete)
        layout.addWidget(buttons)
        if self._edges:
            self._sync(0)

    def _sync(self, idx: int):
        if 0 <= idx < len(self._edges):
            self._idx = idx
            self._rel.setText(self._edges[idx].relation_type)

    def _accept_update(self):
        text = self._rel.text().strip()
        if not text:
            QMessageBox.warning(self, "Edit Edge", "Relation type cannot be empty.")
            return
        self._mode = "update"
        self.accept()

    def _accept_delete(self):
        self._mode = "delete"
        self.accept()

    def result(self) -> Tuple[str, int, str]:
        return self._mode, self._idx, self._rel.text().strip()


class DeleteNodeDialog(QDialog):
    def __init__(self, parent, node_ids: List[str]):
        super().__init__(parent)
        self.setWindowTitle("Delete Node")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select node to delete:"))
        self._combo = QComboBox()
        self._combo.addItems(node_ids)
        layout.addWidget(self._combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result(self) -> str:
        return self._combo.currentText()
