from __future__ import annotations


import math
from typing import Any, Dict, List, Optional


from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
QWidget,
QVBoxLayout,
QHBoxLayout,
QPushButton,
QListWidget,
QListWidgetItem,
QSplitter,
QGraphicsScene,
QLabel,
QDialog,
QLineEdit,
QComboBox,
QDialogButtonBox,
QMessageBox,
QTreeWidget,
QTreeWidgetItem,
QCheckBox,
)


# framework imports
from framework.graph_schema import (
GraphDocument,
GraphNode,
GraphEdge,
graph_from_dict,
graph_to_dict,
)


# local split modules
from .graph_view import _NodeGraphicsView
from .graph_nodes import _GraphNodeItem
from .graph_edges import _GraphEdgeItem




class GraphExplorerPanel(QWidget):
"""Dockable panel providing a Blender-like node editor."""


REQUIRED_METADATA_KEYS = ["persona_hint", "descriptor"]


def __init__(self, framework):
super().__init__()
self.framework = framework
self.log = framework.log_manager
self.graph_service = framework.graph_service
self.graph_registry = framework.graph_registry


self._graph_list: QListWidget
self._scene: QGraphicsScene
self._view: _NodeGraphicsView
self._detail_tree: QTreeWidget
self._summary_label: QLabel
self._snap_checkbox: QCheckBox


self._current_graph_id: Optional[str] = None
self._current_graph: Optional[GraphDocument] = None
self._graph_dirty: bool = False
buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBo