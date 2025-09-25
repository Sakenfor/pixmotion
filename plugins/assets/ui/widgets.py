# D:/My Drive/code/pixmotion/plugins/assets/widgets.py
import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QToolButton,
    QLabel,
    QHBoxLayout,
    QStackedWidget,
    QStyle,
    QComboBox,
)
from PyQt6.QtCore import Qt, QSize, QUrl, QEvent, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPolygonF, QColor
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from .views import ImageViewer


class AssetBrowserTitleBar(QWidget):
    """A custom title bar for the Asset Browser dock with integrated filter controls."""

    add_folder_clicked = pyqtSignal()
    rating_filter_changed = pyqtSignal(int)
    type_filter_changed = pyqtSignal(str)

    def __init__(self, title="Asset Browser", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(6)

        layout.addWidget(QLabel(f"<b>{title}</b>"))
        layout.addStretch()

        # --- Add Folder Button ---
        add_folder_btn = QToolButton()
        add_folder_btn.setText("Add Folder")
        add_folder_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        add_folder_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        add_folder_btn.clicked.connect(self.add_folder_clicked.emit)
        layout.addWidget(add_folder_btn)

        # --- Filter Controls ---
        layout.addWidget(QLabel("Filter:"))
        star_filter = StarRatingFilter()
        star_filter.filter_changed.connect(self.rating_filter_changed.emit)
        layout.addWidget(star_filter)

        type_filter_combo = QComboBox()
        type_filter_combo.addItems(["All", "Image", "Video"])
        type_filter_combo.currentTextChanged.connect(
            lambda text: self.type_filter_changed.emit(text.lower())
        )
        layout.addWidget(type_filter_combo)


class PreviewPopup(QWidget):
    """A floating window for asset previews on hover, supporting images and video."""

    def __init__(self, parent=None):
        super().__init__(
            parent, Qt.WindowType.ToolTip | Qt.WindowType.BypassWindowManagerHint
        )
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setFixedSize(256, 256)
        self.setStyleSheet("background-color: #2c2c2c; border: 1px solid #555;")

        self.stacked_widget = QStackedWidget()
        self.layout().addWidget(self.stacked_widget)

        self.image_viewer = ImageViewer()
        self.stacked_widget.addWidget(self.image_viewer)

        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.stacked_widget.addWidget(self.video_widget)

    def show_preview(self, path):
        _, ext = os.path.splitext(path.lower())
        if ext in [".mp4", ".mov", ".avi"]:
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.stacked_widget.setCurrentWidget(self.video_widget)
            self.media_player.play()
        else:
            pixmap = QPixmap(path)
            self.image_viewer.set_pixmap(pixmap)
            self.stacked_widget.setCurrentWidget(self.image_viewer)

        self.move(QCursor.pos().x() + 15, QCursor.pos().y() + 15)
        self.show()

    def hide_popup(self):
        self.media_player.stop()
        self.hide()


class AssetHoverManager(QWidget):
    """Manages showing a preview popup on hover for the asset view."""

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.popup = PreviewPopup()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.ToolTip:
            index = self.view.indexAt(event.pos())
            if index.isValid():
                asset_data = index.data(Qt.ItemDataRole.UserRole)
                if asset_data and asset_data.get("path"):
                    self.popup.show_preview(asset_data["path"])
                    return True
            self.popup.hide_popup()
        if event.type() == QEvent.Type.Leave:
            self.popup.hide_popup()
        return super().eventFilter(source, event)


class StarRatingFilter(QWidget):
    """A widget for filtering assets by star rating."""

    filter_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rating = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.star_size = 14
        self.star_spacing = 4
        self.active_color = QColor("#ffc107")
        self.inactive_color = QColor("#555555")

    def set_rating(self, rating):
        if self._rating != rating:
            self._rating = rating
            self.update()
            self.filter_changed.emit(self._rating)

    def set_colors(self, active_color: QColor | str, inactive_color: QColor | str):
        """Update the star colors based on the active theme."""
        self.active_color = QColor(active_color)
        self.inactive_color = QColor(inactive_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        star_polygon = QPolygonF(
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
        for i in range(5):
            painter.save()
            painter.translate(i * (self.star_size + self.star_spacing), 0)
            painter.scale(self.star_size, self.star_size)
            painter.setBrush(self.active_color if i < self._rating else self.inactive_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(star_polygon)
            painter.restore()

    def mousePressEvent(self, event):
        click_x = event.pos().x()
        new_rating = int(click_x / (self.star_size + self.star_spacing)) + 1
        if new_rating > 5:
            new_rating = 5
        self.set_rating(0 if new_rating == self._rating else new_rating)

    def minimumSizeHint(self):
        width = 5 * self.star_size + 4 * self.star_spacing
        height = self.star_size + 2
        return QSize(width, height)
