from __future__ import annotations
import typing
from enum import Enum
from PyQt6.QtCore import QPointF, pyqtSignal, QRectF, Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QKeyEvent, QPainterPath, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QGraphicsPathItem

# Forward declare to avoid circular imports, for type hints only
if typing.TYPE_CHECKING:
    from .graph_nodes import _Socket, _GraphNodeItem
    from .graph_edges import _GraphEdgeItem

# A known MIME type is required for inter-widget drag-and-drop
ASSET_MIME_TYPE = "application/x-story-studio-asset-id"


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


class InteractionMode(Enum):
    """Defines the current interaction state of the view."""
    DEFAULT = 0
    DRAGGING_EDGE = 1
    REWIRE_EDGE = 2


class _NodeGraphicsView(QGraphicsView):
    request_add_node = pyqtSignal(QPointF)
    request_delete_selection = pyqtSignal()
    edge_dropped = pyqtSignal(object, object)
    edge_rewired = pyqtSignal(object, bool, object)
    # *** CHANGE: New signal for asset drops ***
    asset_dropped_on_node = pyqtSignal(str, str)  # asset_id, node_id

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        # *** CHANGE: Enable drop events ***
        self.setAcceptDrops(True)
        self._drag_over_node: _GraphNodeItem | None = None

        self._grid_size = 24
        self._show_grid = True
        self._snap_to_grid = True
        self._interaction_mode = InteractionMode.DEFAULT
        self._drag_item = None
        self._preview_edge: QGraphicsPathItem | None = None
        self._pen_preview_default = QPen(QColor(220, 220, 220, 180), 2, Qt.PenStyle.DashLine)
        self._pen_preview_default.setCosmetic(True)
        self._pen_preview_valid = QPen(QColor(80, 250, 80, 220), 2.5, Qt.PenStyle.SolidLine)
        self._pen_preview_valid.setCosmetic(True)

    # *** CHANGE: Add drag and drop event handlers ***
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(ASSET_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        from .graph_nodes import _GraphNodeItem

        target_item = self.itemAt(event.pos())
        node_item = target_item if isinstance(target_item, _GraphNodeItem) else None

        if self._drag_over_node != node_item:
            if self._drag_over_node:
                self._drag_over_node.set_highlight(False)  # Turn off old highlight

            self._drag_over_node = node_item

            if self._drag_over_node:
                self._drag_over_node.set_highlight(True)  # Turn on new highlight

        if node_item:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        if self._drag_over_node:
            self._drag_over_node.set_highlight(False)
            self._drag_over_node = None
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        if self._drag_over_node and event.mimeData().hasFormat(ASSET_MIME_TYPE):
            asset_id_bytes = event.mimeData().data(ASSET_MIME_TYPE)
            asset_id = asset_id_bytes.data().decode()
            node_id = self._drag_over_node.node.id
            self.asset_dropped_on_node.emit(asset_id, node_id)
            event.acceptProposedAction()

        if self._drag_over_node:
            self._drag_over_node.set_highlight(False)
            self._drag_over_node = None

    # ... (rest of the file is unchanged)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            if self._interaction_mode != InteractionMode.DEFAULT:
                self._cancel_drag()
                event.accept()
                return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.request_delete_selection.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        if self._interaction_mode != InteractionMode.DEFAULT:
            scene_pos = self.mapToScene(event.pos())
            self._update_drag_preview(scene_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._interaction_mode != InteractionMode.DEFAULT:
            target_item = self.itemAt(event.pos())
            from .graph_nodes import _Socket
            target_socket: _Socket | None = target_item if isinstance(target_item, _Socket) else None

            if self._interaction_mode == InteractionMode.DRAGGING_EDGE:
                source_socket: _Socket = self._drag_item
                self.edge_dropped.emit(source_socket, target_socket)
            elif self._interaction_mode == InteractionMode.REWIRE_EDGE:
                edge_item: _GraphEdgeItem
                is_source: bool
                edge_item, is_source = self._drag_item
                self.edge_rewired.emit(edge_item, is_source, target_socket)

            self._cancel_drag()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def start_edge_drag(self, socket: _Socket):
        self._interaction_mode = InteractionMode.DRAGGING_EDGE
        self._drag_item = socket
        self._create_preview_edge(p1=socket.scenePos())
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def start_edge_rewire(self, edge_item: _GraphEdgeItem, is_source_endpoint: bool):
        self._interaction_mode = InteractionMode.REWIRE_EDGE
        self._drag_item = (edge_item, is_source_endpoint)
        edge_item.setVisible(False)
        fixed_pos = edge_item._p2 if is_source_endpoint else edge_item._p1
        self._create_preview_edge(p1=fixed_pos)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def _is_valid_connection(self, target_socket: typing.Optional["_Socket"]) -> bool:
        if not target_socket:
            return False

        if self._interaction_mode == InteractionMode.DRAGGING_EDGE:
            source_socket: "_Socket" = self._drag_item
            return (source_socket.parent_node != target_socket.parent_node and
                    source_socket.is_output != target_socket.is_output)

        elif self._interaction_mode == InteractionMode.REWIRE_EDGE:
            edge_item: "_GraphEdgeItem"
            is_source_dragged: bool
            edge_item, is_source_dragged = self._drag_item

            if is_source_dragged:
                return (target_socket.is_output and
                        target_socket.parent_node != edge_item.target_node_item)
            else:
                return (not target_socket.is_output and
                        target_socket.parent_node != edge_item.source_node_item)

        return False

    def _create_preview_edge(self, p1: QPointF):
        self._preview_edge = QGraphicsPathItem()
        self._preview_edge.setPen(self._pen_preview_default)
        self._preview_edge.setZValue(10)
        self.scene().addItem(self._preview_edge)
        self._update_drag_preview(p1)

    def _update_drag_preview(self, scene_pos: QPointF):
        if not self._preview_edge: return

        from .graph_nodes import _Socket
        target_item = self.itemAt(self.mapFromScene(scene_pos))
        target_socket = target_item if isinstance(target_item, _Socket) else None

        is_valid = self._is_valid_connection(target_socket)

        end_pos = target_socket.scenePos() if is_valid else scene_pos
        self._preview_edge.setPen(self._pen_preview_valid if is_valid else self._pen_preview_default)

        if self._interaction_mode == InteractionMode.DRAGGING_EDGE:
            start_pos = self._drag_item.scenePos()
            path = make_bezier_path(start_pos, end_pos)
        elif self._interaction_mode == InteractionMode.REWIRE_EDGE:
            edge_item, is_source = self._drag_item
            fixed_pos = edge_item._p2 if is_source else edge_item._p1
            start_pos = end_pos if is_source else fixed_pos
            path_end_pos = fixed_pos if is_source else end_pos
            path = make_bezier_path(start_pos, path_end_pos)
        else:
            return

        self._preview_edge.setPath(path)
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if is_valid else Qt.CursorShape.ForbiddenCursor)

    def _cancel_drag(self):
        if self._preview_edge:
            self.scene().removeItem(self._preview_edge)
            self._preview_edge = None
        if self._interaction_mode == InteractionMode.REWIRE_EDGE:
            edge_item, _ = self._drag_item
            edge_item.setVisible(True)
        self._interaction_mode = InteractionMode.DEFAULT
        self._drag_item = None
        self.viewport().unsetCursor()

    def set_grid_visible(self, visible: bool):
        self._show_grid = bool(visible)
        self.viewport().update()

    def set_snap_enabled(self, enabled: bool):
        self._snap_to_grid = bool(enabled)

    def snap_point(self, pt: QPointF) -> QPointF:
        if not self._snap_to_grid: return pt
        g = float(self._grid_size)
        return QPointF(round(pt.x() / g) * g, round(pt.y() / g) * g)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor
        old_pos = self.mapToScene(event.position().toPoint())
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        add_node = menu.addAction("Add Node")
        menu.addSeparator()
        fit_view = menu.addAction("Frame All")
        toggle_grid = menu.addAction("Hide Grid" if self._show_grid else "Show Grid")
        toggle_snap = menu.addAction("Disable Snap" if self._snap_to_grid else "Enable Snap")
        chosen = menu.exec(event.globalPos())
        if chosen == add_node:
            self.request_add_node.emit(self.mapToScene(event.pos()))
        elif chosen == fit_view and self.scene().itemsBoundingRect().isValid():
            self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        elif chosen == toggle_grid:
            self.set_grid_visible(not self._show_grid)
        elif chosen == toggle_snap:
            self.set_snap_enabled(not self._snap_to_grid)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        if not self._show_grid:
            super().drawBackground(painter, rect)
            return
        painter.fillRect(rect, QColor("#242424"))
        fine = self._grid_size
        left = int(rect.left() / fine) * fine
        top = int(rect.top() / fine) * fine

        lines = []
        pen_minor = QPen(QColor(60, 60, 60), 1)
        painter.setPen(pen_minor)
        x = left
        while x < rect.right():
            lines.append(QPointF(x, rect.top()))
            lines.append(QPointF(x, rect.bottom()))
            x += fine
        y = top
        while y < rect.bottom():
            lines.append(QPointF(rect.left(), y))
            lines.append(QPointF(rect.right(), y))
            y += fine
        painter.drawLines(lines)

