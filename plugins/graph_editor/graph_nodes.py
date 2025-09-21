from __future__ import annotations
import typing
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPainterPath
from PyQt6.QtWidgets import QGraphicsObject, QGraphicsEllipseItem, QMenu

if typing.TYPE_CHECKING:
    from .graph_view import _NodeGraphicsView
    from .graph_edges import _GraphEdgeItem


class _Socket(QGraphicsEllipseItem):
    """Small circular socket for input/output connections."""

    def __init__(self, parent: "_GraphNodeItem", is_output: bool, row: int):
        radius = 6
        super().__init__(-radius, -radius, radius * 2, radius * 2, parent)
        self.parent_node = parent
        self.is_output = is_output
        self.row = row
        self.setBrush(QBrush(QColor("#1e1e1e")))
        self.setPen(QPen(QColor("#f8c555"), 1))
        self.setZValue(parent.zValue() + 0.2)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setToolTip("Output" if is_output else "Input")
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if view := self._get_view():
                view.start_edge_drag(self)
                event.accept()
                return
        super().mousePressEvent(event)

    def _get_view(self) -> _NodeGraphicsView | None:
        return self.scene().views()[0] if self.scene() and self.scene().views() else None


class _GraphNodeItem(QGraphicsObject):
    """Rounded-rectangle node with sockets and drag-move behaviour."""

    def __init__(self, panel, node, position: QPointF, width: float = 200.0):
        super().__init__()
        self.panel = panel
        self.node = node
        self.width = width
        self._row_height = 22
        self._padding = 10
        self._title_h = 28
        self._radius = 12
        self._rows = 1
        # *** CHANGE: Add state for highlight ***
        self._is_highlighted = False

        self._inputs: list[_Socket] = []
        self._outputs: list[_Socket] = []
        self.edge_items: set[_GraphEdgeItem] = set()

        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1)
        self.setPos(position)

        self._build_initial_sockets()
        self._layout_sockets()

    # *** CHANGE: Add method to control highlighting ***
    def set_highlight(self, highlighted: bool):
        if self._is_highlighted != highlighted:
            self._is_highlighted = highlighted
            self.update()  # Trigger a repaint

    def add_edge(self, edge: _GraphEdgeItem):
        self.edge_items.add(edge)

    def remove_edge(self, edge: _GraphEdgeItem):
        self.edge_items.discard(edge)

    def update_edges(self):
        for edge in self.edge_items:
            edge.update_positions()

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionChange and self.scene():
            if view := self.scene().views()[0]:
                value = view.snap_point(value)
            self.panel._on_node_moved(self)
        elif change == self.GraphicsItemChange.ItemPositionHasChanged:
            self.update_edges()
        return super().itemChange(change, value)

    def _body_rect(self) -> QRectF:
        h = self._title_h + self._padding * 2 + self._rows * self._row_height
        return QRectF(0, 0, self.width, h)

    def _title_rect(self) -> QRectF:
        r = self._body_rect()
        return QRectF(r.left(), r.top(), r.width(), self._title_h)

    def boundingRect(self) -> QRectF:
        return self._body_rect().adjusted(-8, -8, 8, 8)

    def _build_initial_sockets(self):
        layout_cfg = self.panel._get_node_layout_cfg(self.node.id)
        in_count = int(layout_cfg.get("inputs", 1))
        out_count = int(layout_cfg.get("outputs", 1))
        self.set_socket_counts(in_count, out_count, persist=False)

    def set_socket_counts(self, inputs: int, outputs: int, persist: bool = True):
        for s in self._inputs + self._outputs:
            if s.scene(): s.scene().removeItem(s)
        self._inputs.clear()
        self._outputs.clear()

        self._rows = max(1, int(inputs), int(outputs))
        for i in range(int(inputs)):
            self._inputs.append(_Socket(self, is_output=False, row=i))
        for i in range(int(outputs)):
            self._outputs.append(_Socket(self, is_output=True, row=i))

        self.prepareGeometryChange()
        self._layout_sockets()
        if persist:
            self.panel._save_node_socket_counts(self.node.id, len(self._inputs), len(self._outputs))
        self.update_edges()

    def _layout_sockets(self):
        r = self._body_rect()
        y0 = r.top() + self._title_h + self._padding + self._row_height / 2
        for i, sock in enumerate(self._inputs):
            sock.setPos(r.left(), y0 + i * self._row_height)
        for i, sock in enumerate(self._outputs):
            sock.setPos(r.right(), y0 + i * self._row_height)

    def input_pos(self, index: int) -> QPointF:
        if not self._inputs: return self.scenePos()
        return self._inputs[max(0, min(index, len(self._inputs) - 1))].scenePos()

    def output_pos(self, index: int) -> QPointF:
        if not self._outputs: return self.scenePos()
        return self._outputs[max(0, min(index, len(self._outputs) - 1))].scenePos()

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = self._body_rect()
        shadow = QPainterPath()
        shadow.addRoundedRect(body.adjusted(3, 4, 3, 4), self._radius, self._radius)
        painter.fillPath(shadow, QColor(0, 0, 0, 120))
        card = QPainterPath()
        card.addRoundedRect(body, self._radius, self._radius)
        color = _color_for_type(self.node.type)
        painter.fillPath(card, color)

        # *** CHANGE: Update paint logic for highlighting ***
        if self._is_highlighted:
            pen = QPen(QColor(80, 250, 80), 3)
            pen.setStyle(Qt.PenStyle.DashLine)
        elif self.isSelected():
            pen = QPen(QColor("#f8c555"), 2.5)
        else:
            pen = QPen(color.darker(160), 2)
        painter.setPen(pen)
        painter.drawPath(card)

        header = self._title_rect()
        header_path = QPainterPath()
        header_path.addRoundedRect(header, self._radius, self._radius)
        header_path.addRect(header.left(), header.bottom() - self._radius, header.width(), self._radius)
        painter.fillPath(header_path, color.darker(120))
        painter.setPen(QColor("#f0f0f0"))
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(header.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignVCenter, self.node.label or self.node.id)
        self.setToolTip(f"{self.node.id}\n{self.node.type}")

    def contextMenuEvent(self, event):
        menu = QMenu()
        add_in = menu.addAction("Add Input Socket")
        add_out = menu.addAction("Add Output Socket")
        rem_in = menu.addAction("Remove Last Input")
        rem_out = menu.addAction("Remove Last Output")
        chosen = menu.exec(event.screenPos())

        if chosen == add_in:
            self.set_socket_counts(len(self._inputs) + 1, len(self._outputs))
        elif chosen == add_out:
            self.set_socket_counts(len(self._inputs), len(self._outputs) + 1)
        elif chosen == rem_in and len(self._inputs) > 0:
            self.set_socket_counts(len(self._inputs) - 1, len(self._outputs))
        elif chosen == rem_out and len(self._outputs) > 0:
            self.set_socket_counts(len(self._inputs), len(self._outputs) - 1)

        if chosen:
            self.panel._mark_dirty(True)


def _color_for_type(type_name: str) -> QColor:
    if not type_name: return QColor("#3a87c8")
    seed = sum(ord(ch) for ch in type_name)
    return QColor(90 + (seed * 37) % 130, 100 + (seed * 53) % 120, 110 + (seed * 71) % 110)

