# D:/My Drive/code/pixmotion/plugins/assets/views.py
import os
from PyQt6.QtCore import (
    QAbstractListModel,
    Qt,
    QSize,
    QRect,
    QEvent,
    pyqtSignal,
    QPointF,
    QModelIndex,
    QRectF,
    QMimeData,
)
from PyQt6.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QPolygonF,
    QIcon,
    QBrush,
    QPainterPath,
)
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QWidget
from plugins.core.models import Asset


class AssetModel(QAbstractListModel):
    """A model to display assets from the database."""

    thumbnail_requested = pyqtSignal(QModelIndex, str, str)
    MIME_TYPE = "application/x-story-studio-asset-id"

    def __init__(self, log, parent=None):
        super().__init__(parent)
        self.log = log
        self.assets = []

    def rowCount(self, parent=None):
        return len(self.assets)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.assets)):
            return None
        asset = self.assets[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return os.path.basename(asset.path)
        if role == Qt.ItemDataRole.DecorationRole:
            if hasattr(asset, "thumbnail_pixmap") and asset.thumbnail_pixmap:
                return asset.thumbnail_pixmap
            self.thumbnail_requested.emit(index, asset.path, asset.id)
            return QIcon()
        if role == Qt.ItemDataRole.UserRole:
            return {"id": asset.id, "path": asset.path, "rating": asset.rating, "type": asset.asset_type.value}
        return None

    # *** CHANGE: Enable dragging by overriding flags() ***
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        default_flags = super().flags(index)
        if index.isValid():
            return default_flags | Qt.ItemFlag.ItemIsDragEnabled
        return default_flags

    # *** CHANGE: Package asset data for drag operations ***
    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        mime_data = QMimeData()
        if not indexes:
            return mime_data

        index = indexes[0]
        if not index.isValid():
            return mime_data

        asset_data = self.data(index, Qt.ItemDataRole.UserRole)
        if asset_data and "id" in asset_data:
            asset_id = asset_data["id"]
            # We encode the asset ID as bytes for the custom MIME type
            encoded_data = asset_id.encode()
            mime_data.setData(self.MIME_TYPE, encoded_data)
            self.log.info(f"Starting drag for asset ID: {asset_id}")

        return mime_data

    def cache_thumbnail(self, asset_id, pixmap):
        """Finds the asset by ID and caches the loaded pixmap on it."""
        for i, asset in enumerate(self.assets):
            if asset.id == asset_id:
                asset.thumbnail_pixmap = pixmap
                index = self.index(i)
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])
                return

    def set_assets(self, assets):
        self.beginResetModel()
        self.assets = sorted(assets, key=lambda a: a.path)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.assets = []
        self.endResetModel()

    def get_all_assets(self):
        """Returns the current list of asset data dictionaries."""
        return [
            self.data(self.index(i), Qt.ItemDataRole.UserRole)
            for i in range(self.rowCount())
        ]


class AssetDelegate(QStyledItemDelegate):
    """A delegate to custom-draw assets in the list view with interactive ratings."""

    rating_changed = pyqtSignal(str, int)

    def __init__(
        self,
        parent=None,
        *,
        thumbnail_size: int = 128,
        star_size: int = 16,
        padding: int = 8,
        star_spacing: int = 4,
    ) -> None:
        super().__init__(parent)
        self.thumbnail_size = thumbnail_size
        self.star_size = star_size
        self.star_spacing = star_spacing
        self.padding = padding
        self.star_count = 5
        self.star_row_height = self.star_size + 6
        self.footer_height = self.star_row_height
        self._item_width = self.thumbnail_size + 2 * self.padding
        self._item_height = self.thumbnail_size + self.footer_height + 2 * self.padding
        self._item_size = QSize(self._item_width, self._item_height)

        self._unit_star = QPolygonF(
            [
                QPointF(0.5, 0.0),
                QPointF(0.61, 0.35),
                QPointF(1.0, 0.35),
                QPointF(0.68, 0.6),
                QPointF(0.79, 0.95),
                QPointF(0.5, 0.7),
                QPointF(0.21, 0.95),
                QPointF(0.32, 0.6),
                QPointF(0.0, 0.35),
                QPointF(0.39, 0.35),
            ]
        )
        self._star_on = self._build_star_pixmap(QColor("#ffc107"))
        self._star_off = self._build_star_pixmap(QColor("#555555"))

    def _build_star_pixmap(self, color: QColor) -> QPixmap:
        pixmap = QPixmap(self.star_size, self.star_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        pad = 1.0
        scale = self.star_size - 2 * pad
        points = [
            QPointF(pad + pt.x() * scale, pad + pt.y() * scale)
            for pt in self._unit_star
        ]
        painter.drawPolygon(QPolygonF(points))
        painter.end()
        return pixmap

    def item_size(self) -> QSize:
        return QSize(self._item_width, self._item_height)

    def sizeHint(self, option, index):  # noqa: D401 - Qt signature
        return self.item_size()

    def _content_rect(self, option_rect: QRect) -> QRect:
        return option_rect.adjusted(
            self.padding, self.padding, -self.padding, -self.padding
        )

    def _thumbnail_rect(self, content_rect: QRect) -> QRect:
        available_height = max(0, content_rect.height() - self.footer_height)
        side = min(
            self.thumbnail_size,
            available_height if available_height > 0 else self.thumbnail_size,
            content_rect.width(),
        )
        side = max(1, side)
        x = content_rect.center().x() - side // 2
        return QRect(x, content_rect.top(), side, side)

    def _star_rect(self, content_rect: QRect) -> QRect:
        return QRect(
            content_rect.left(),
            content_rect.bottom() - self.footer_height + 1,
            content_rect.width(),
            self.footer_height - 1,
        )

    def paint(self, painter: QPainter, option, index):
        asset_data = index.data(Qt.ItemDataRole.UserRole) or {}
        pixmap = index.data(Qt.ItemDataRole.DecorationRole)
        rating = asset_data.get("rating", 0)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        content_rect = self._content_rect(option.rect)
        thumb_rect = self._thumbnail_rect(content_rect)
        star_rect = self._star_rect(content_rect)

        if isinstance(pixmap, QPixmap) and not pixmap.isNull() and thumb_rect.isValid():
            path = QPainterPath()
            path.addRoundedRect(QRectF(thumb_rect), 10.0, 10.0)
            painter.setClipPath(path)
            painter.drawPixmap(thumb_rect, pixmap, pixmap.rect())
            painter.setClipping(False)
        else:
            painter.setPen(QColor("#444"))
            painter.drawText(
                thumb_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Loading...",
            )

        self._paint_stars(painter, star_rect, rating)
        painter.restore()

    def _paint_stars(self, painter: QPainter, rect: QRect, rating: int) -> None:
        painter.save()
        total_width = (
            self.star_count * self.star_size + (self.star_count - 1) * self.star_spacing
        )
        start_x = rect.x() + max(0, (rect.width() - total_width) // 2)
        y = rect.y() + max(0, (rect.height() - self.star_size) // 2)

        for i in range(self.star_count):
            pixmap = self._star_on if i < rating else self._star_off
            painter.drawPixmap(
                start_x + i * (self.star_size + self.star_spacing), y, pixmap
            )
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            star_rect = self._star_rect(self._content_rect(option.rect))
            if star_rect.contains(event.pos()):
                total_width = (
                    self.star_count * self.star_size
                    + (self.star_count - 1) * self.star_spacing
                )
                start_x = star_rect.x() + max(0, (star_rect.width() - total_width) // 2)
                relative_x = event.pos().x() - start_x
                new_rating = int(relative_x / (self.star_size + self.star_spacing)) + 1
                new_rating = max(1, min(self.star_count, new_rating))

                asset_data = index.data(Qt.ItemDataRole.UserRole) or {}
                asset_id = asset_data.get("id")
                current_rating = asset_data.get("rating", 0)
                if new_rating == current_rating:
                    new_rating = 0
                self.rating_changed.emit(asset_id, new_rating)
                return True

        return super().editorEvent(event, model, option, index)


class ImageViewer(QWidget):
    """A simple widget that just displays a pixmap, scaled to fit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None

    def set_pixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        if not self._pixmap:
            return
        painter = QPainter(self)
        scaled_pixmap = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)

