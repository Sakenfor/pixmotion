# D:/My Drive/code/pixmotion/plugins/assets/views.py
import os
from PyQt6.QtCore import QAbstractListModel, Qt, QSize, QRect, QEvent, pyqtSignal, QPointF, QModelIndex, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygonF, QIcon, QBrush, QPainterPath
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QWidget
from core.models import Asset


class AssetModel(QAbstractListModel):
    """A model to display assets from the database."""
    thumbnail_requested = pyqtSignal(QModelIndex, str, str)

    def __init__(self, log, parent=None):
        super().__init__(parent)
        self.log = log
        self.assets = []

    def rowCount(self, parent=None):
        return len(self.assets)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        # --- FIX: Add a bounds check to prevent crashes during model updates ---
        if not index.isValid() or not (0 <= index.row() < len(self.assets)):
            return None
        asset = self.assets[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return os.path.basename(asset.path)
        if role == Qt.ItemDataRole.DecorationRole:
            # --- FIX: Check for the cached pixmap before re-requesting ---
            if hasattr(asset, 'thumbnail_pixmap') and asset.thumbnail_pixmap:
                return asset.thumbnail_pixmap

            # If not cached, request the thumbnail to be loaded
            self.thumbnail_requested.emit(index, asset.path, asset.id)
            return QIcon()  # Return an empty icon
        if role == Qt.ItemDataRole.UserRole:  # Custom role to get all data
            return {
                'id': asset.id,
                'path': asset.path,
                'rating': asset.rating
            }
        return None

    def cache_thumbnail(self, asset_id, pixmap):
        """Finds the asset by ID and caches the loaded pixmap on it."""
        for i, asset in enumerate(self.assets):
            if asset.id == asset_id:
                # --- FIX: Actually store the pixmap on the model item ---
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
        return [self.data(self.index(i), Qt.ItemDataRole.UserRole) for i in range(self.rowCount())]


class AssetDelegate(QStyledItemDelegate):
    """A delegate to custom-draw assets in the list view with interactive ratings."""
    rating_changed = pyqtSignal(str, int)

    def paint(self, painter: QPainter, option, index):
        asset_data = index.data(Qt.ItemDataRole.UserRole) or {}
        pixmap = index.data(Qt.ItemDataRole.DecorationRole)  # This will be a QPixmap or QIcon
        rating = asset_data.get('rating', 0)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing) # For smooth corners

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        thumb_rect = QRect(option.rect.x(), option.rect.y(), option.rect.width(), option.rect.height() - 15)

        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            # --- FIX: Calculate a centered square to draw in, ensuring no distortion ---
            side = min(thumb_rect.width(), thumb_rect.height())
            centered_square_rect = QRect(
                thumb_rect.x() + (thumb_rect.width() - side) // 2,
                thumb_rect.y() + (thumb_rect.height() - side) // 2,
                side,
                side
            )

            # --- Re-introduce rounded corners using a clipping path ---
            path = QPainterPath()
            path.addRoundedRect(QRectF(centered_square_rect), 8.0, 8.0)  # 8px corner radius
            painter.setClipPath(path)

            # Use the robust drawPixmap overload that specifies source and target rects
            painter.drawPixmap(centered_square_rect, pixmap, pixmap.rect())
        else:
            # Draw a placeholder if no thumbnail yet
            painter.setPen(QColor("#444"))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "Loading...")

        # Always draw stars
        star_area_rect = QRect(option.rect.x(), option.rect.y() + option.rect.height() - 15, option.rect.width(), 15)
        self.paint_stars(painter, star_area_rect, rating)

        painter.restore()

    def paint_stars(self, painter, rect, rating):
        painter.save()
        star_polygon = QPolygonF([
            QPointF(0.5, 0.0), QPointF(0.61, 0.35), QPointF(1.0, 0.35),
            QPointF(0.68, 0.6), QPointF(0.79, 0.95), QPointF(0.5, 0.7),
            QPointF(0.21, 0.95), QPointF(0.32, 0.6), QPointF(0.0, 0.35),
            QPointF(0.39, 0.35)
        ])

        star_size = 12
        total_width = 5 * star_size + 4 * 2
        start_x = rect.x() + (rect.width() - total_width) // 2

        for i in range(5):
            painter.save()
            painter.translate(start_x + i * (star_size + 2), rect.y() + (rect.height() - star_size) // 2)
            painter.scale(star_size, star_size)

            if i < rating:
                painter.setBrush(QColor("#ffc107"))  # Gold
            else:
                painter.setBrush(QColor("#555"))  # Dark Gray
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(star_polygon)
            painter.restore()
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            star_area_rect = QRect(option.rect.x(), option.rect.y() + option.rect.height() - 15, option.rect.width(),
                                   15)
            if star_area_rect.contains(event.pos()):
                star_size = 12
                total_width = 5 * star_size + 4 * 2
                start_x = star_area_rect.x() + (star_area_rect.width() - total_width) // 2
                click_x = event.pos().x() - start_x

                new_rating = int(click_x / (star_size + 2)) + 1
                if new_rating < 1: new_rating = 1
                if new_rating > 5: new_rating = 5

                asset_data = index.data(Qt.ItemDataRole.UserRole)
                asset_id = asset_data.get('id')
                current_rating = asset_data.get('rating', 0)

                if new_rating == current_rating:
                    new_rating = 0  # Allow un-rating by clicking the same star

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
            Qt.TransformationMode.SmoothTransformation
        )
        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)