from __future__ import annotations
import typing
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPainter
from PyQt6.QtWidgets import QGraphicsPathItem, QMenu

if typing.TYPE_CHECKING:
    from .graph_view import _NodeGraphicsView
    from .graph_nodes import _GraphNodeItem


def _control_points(p1: QPointF, p2: QPointF, strength: float = 0.5):
    dx = p2.x() - p1.x()
    c1 = QPointF(p1.x() + dx * strength, p1.y())
    c2 = QPointF(p2.x() - dx * strength, p2.y())
    return c1, c2


def make_bezier_path(p1: QPointF, p2: QPointF) -> QPainterPath:
    c1, c2 = _control_points(p1, p2)
    path = QPainterPath(p1)
    path.cubicTo(c1, c2, p2)
    return path


def _color_for_relation(rel: str) -> QColor:
    palette = {
        "link": QColor("#8a8a8a"),
        "parent": QColor("#4caf50"),
        "conflict": QColor("#f44336"),
        "depends": QColor("#3f51b5"),
    }
    return palette.get(rel, QColor("#8a8a8a"))


class _GraphEdgeItem(QGraphicsPathItem):
    """Bezier edge that supports selection, hover highlight, and drag-to-rewire."""

    def __init__(self, index: int, source_id: str, target_id: str, relation: str):
        super().__init__()
        self.index = index
        self.source_id = source_id
        self.target_id = target_id
        self.relation = relation

        self.source_node_item: _GraphNodeItem | None = None
        self.target_node_item: _GraphNodeItem | None = None

        base_color = _color_for_relation(relation)
        self._base_pen = QPen(base_color, 2)
        self._hover_pen = QPen(QColor("#e3e3e3"), 3)
        self._sel_pen = QPen(QColor("#f8c555"), 3)
        self.setPen(self._base_pen)
        self.setZValue(0)
        self.setAcceptHoverEvents(True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setToolTip(f"{self.source_id} → {self.target_id}\n{self.relation}")
        self._p1 = QPointF(0, 0)
        self._p2 = QPointF(0, 0)

    def set_node_items(self, source: _GraphNodeItem, target: _GraphNodeItem):
        self.source_node_item = source
        self.target_node_item = target
        source.add_edge(self)
        target.add_edge(self)

    def update_positions(self):
        if not self.source_node_item or not self.target_node_item:
            return
        # Choose socket rows using relation hash against available sockets
        s_outputs = self.source_node_item._outputs
        t_inputs = self.target_node_item._inputs
        s_row = 0 if not s_outputs else abs(hash(self.relation)) % len(s_outputs)
        t_row = 0 if not t_inputs else abs(hash(self.relation)) % len(t_inputs)
        p1 = self.source_node_item.output_pos(s_row)
        p2 = self.target_node_item.input_pos(t_row)
        self._p1 = p1
        self._p2 = p2
        self.setPath(make_bezier_path(p1, p2))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not (view := self._get_view()): return

            # Determine if user clicked closer to the source or target endpoint
            pos = event.pos()
            dist_source = (pos - self.mapFromScene(self._p1)).manhattanLength()
            dist_target = (pos - self.mapFromScene(self._p2)).manhattanLength()
            dragging_source = dist_source < dist_target

            view.start_edge_rewire(self, dragging_source)
            event.accept()
        else:
            super().mousePressEvent(event)

    def setSelected(self, selected: bool):
        super().setSelected(selected)
        self.setPen(self._sel_pen if selected else self._base_pen)

    def hoverEnterEvent(self, event):
        if not self.isSelected(): self.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self.isSelected(): self.setPen(self._base_pen)
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        rename = menu.addAction("Edit Relation…")
        delete = menu.addAction("Delete Edge")
        chosen = menu.exec(event.screenPos())
        if not (view := self._get_view()) or not hasattr(view.parent(), "panel"): return

        panel = view.parent().panel
        if chosen == rename:
            panel._edit_edge_by_index(self.index)
        elif chosen == delete:
            panel._delete_edge_by_index(self.index)

    def _get_view(self) -> _NodeGraphicsView | None:
        return self.scene().views()[0] if self.scene() and self.scene().views() else None
