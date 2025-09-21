# D:/My Drive/code/pixmotion/plugins/assets/windows.py
import os
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from html import escape
from datetime import datetime
from plugins.core.models import Generation
from .views import ImageViewer



class PromptedVideoWidget(QVideoWidget):
    """Video widget with a semi-transparent prompt overlay."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._overlay = QLabel(self)
        self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 170); color: #f0f0f0; padding: 8px; border-radius: 6px;")
        self._overlay.setTextFormat(Qt.TextFormat.PlainText)
        self._overlay.setWordWrap(True)
        self._overlay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self._overlay.hide()

    def set_prompt_text(self, text: str | None) -> None:
        if text:
            self._overlay.setText(text)
            self._overlay.show()
            self._update_overlay_geometry()
        else:
            self._overlay.hide()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_overlay_geometry()

    def _update_overlay_geometry(self) -> None:
        if not self._overlay.isHidden():
            margin = 12
            max_height = max(60, self.height() // 4)
            width = max(120, self.width() - margin * 2)
            self._overlay.setMaximumWidth(width)
            hint = self._overlay.sizeHint()
            height = min(max_height, hint.height())
            self._overlay.setGeometry(margin, self.height() - height - margin, width, height)

class MediaPreviewWindow(QWidget):
    """A window to preview an asset (image or video) with navigation and metadata."""

    def __init__(self, framework, asset_list, current_index):
        super().__init__()
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.events = framework.get_service("event_manager")
        self.db = framework.get_service("database_service")
        self.asset_list = asset_list
        self.current_index = current_index
        self.creation_prompt = None
        self.current_asset = None
        self.asset_service = framework.get_service("asset_service")
        self._slider_is_pressed = False
        self._media_duration = 0

        self.setWindowTitle("Asset Preview")
        self.setMinimumSize(800, 600)
        self._init_ui()
        self.load_asset()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        content_splitter = QSplitter(Qt.Orientation.Vertical)

        self.stacked_widget = QStackedWidget()
        self.image_viewer = ImageViewer()
        self.stacked_widget.addWidget(self.image_viewer)

        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(4)

        self.video_widget = PromptedVideoWidget()
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)

        video_layout.addWidget(self.video_widget, 1)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.setEnabled(False)
        video_layout.addWidget(self.position_slider)

        self.stacked_widget.addWidget(video_container)
        content_splitter.addWidget(self.stacked_widget)

        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.position_slider.sliderPressed.connect(self._on_slider_pressed)
        self.position_slider.sliderReleased.connect(self._on_slider_released)
        self.position_slider.sliderMoved.connect(self._on_slider_moved)
        self.position_slider.hide()

        metadata_widget = QWidget()
        metadata_layout = QVBoxLayout(metadata_widget)
        self.creation_prompt_label = QLabel("Creation Prompt: N/A")
        self.creation_prompt_label.setWordWrap(True)
        self.creation_prompt_label.setStyleSheet(
            "padding: 5px; background-color: #2a2a2a; border-radius: 4px;"
        )
        self.prompt_history_view = QTextEdit()
        self.prompt_history_view.setReadOnly(True)
        metadata_layout.addWidget(self.creation_prompt_label)
        metadata_layout.addWidget(QLabel("Used As Input In:"))
        metadata_layout.addWidget(self.prompt_history_view)
        content_splitter.addWidget(metadata_widget)
        content_splitter.setSizes([400, 200])

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("< Prev")
        self.use_template_btn = QPushButton("Use as Template")
        self.delete_btn = QPushButton("Delete")
        self.next_btn = QPushButton("Next >")

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.use_template_btn)
        nav_layout.addWidget(self.delete_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)

        main_layout.addWidget(content_splitter)
        main_layout.addLayout(nav_layout)

        self.prev_btn.clicked.connect(self.show_previous)
        self.next_btn.clicked.connect(self.show_next)
        self.use_template_btn.clicked.connect(self._on_use_as_template)
        self.delete_btn.clicked.connect(self._delete_current_asset)
        self.delete_btn.hide()

    def _on_duration_changed(self, duration: int) -> None:
        self._media_duration = max(0, duration)
        self.position_slider.blockSignals(True)
        self.position_slider.setRange(0, self._media_duration if self._media_duration > 0 else 0)
        self.position_slider.setEnabled(self._media_duration > 0)
        if self._media_duration <= 0:
            self.position_slider.setValue(0)
        self.position_slider.blockSignals(False)

    def _on_position_changed(self, position: int) -> None:
        if not self._slider_is_pressed:
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(max(0, position))
            self.position_slider.blockSignals(False)

    def _on_slider_pressed(self) -> None:
        self._slider_is_pressed = True

    def _on_slider_released(self) -> None:
        self._slider_is_pressed = False
        self.media_player.setPosition(self.position_slider.value())

    def _on_slider_moved(self, value: int) -> None:
        if self._slider_is_pressed:
            self.media_player.setPosition(max(0, value))


    def load_asset(self):
        asset_data = self.asset_list[self.current_index]
        self.current_asset = asset_data
        path = asset_data["path"]
        asset_id = asset_data.get("id")

        if not path or not os.path.exists(path):
            self.media_player.stop()
            self.stacked_widget.setCurrentIndex(0)
            self.image_viewer.set_pixmap(QPixmap())
            self.position_slider.setVisible(False)
            self.position_slider.setEnabled(False)
            self.video_widget.set_prompt_text(None)
            self.creation_prompt_label.setText("<b>File Missing</b>")
            self.prompt_history_view.setHtml("Not used as an input yet.")
            self.use_template_btn.hide()
            self.delete_btn.hide()
            return

        _, ext = os.path.splitext(path.lower())

        self.media_player.stop()
        self._slider_is_pressed = False
        self._media_duration = 0
        self.position_slider.blockSignals(True)
        self.position_slider.setRange(0, 0)
        self.position_slider.setValue(0)
        self.position_slider.blockSignals(False)
        self.position_slider.setEnabled(False)
        self.position_slider.setVisible(False)
        self.video_widget.set_prompt_text(None)

        video_extensions = {".mp4", ".mov", ".avi"}
        if ext in video_extensions:
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.stacked_widget.setCurrentIndex(1)
            self.position_slider.setVisible(True)
            self.media_player.play()
        else:
            self.media_player.setSource(QUrl())
            self.position_slider.setVisible(False)
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.image_viewer.set_pixmap(QPixmap())
            else:
                self.image_viewer.set_pixmap(pixmap)
            self.stacked_widget.setCurrentIndex(0)

        creation_generations = self.db.query(
            Generation, lambda g: g.output_asset_id == asset_id
        )
        creation_prompt_text = None
        if creation_generations:
            gen = creation_generations[0]
            creation_prompt_text = gen.prompt or "No prompt provided"
            timestamp = (
                gen.created_at.strftime("%Y-%m-%d %H:%M")
                if getattr(gen, "created_at", None)
                else "Unknown time"
            )
            settings = gen.settings or {}
            meta_parts = []
            model = settings.get("model")
            if model:
                meta_parts.append(f"Model: {model}")
            quality = settings.get("quality")
            if quality:
                meta_parts.append(f"Quality: {quality}")
            duration = settings.get("duration")
            if duration:
                meta_parts.append(f"Duration: {duration}s")
            meta_html = (
                "<br><span style='color:#aaa;'>" + escape(" - ".join(meta_parts)) + "</span>"
                if meta_parts
                else ""
            )
            self.creation_prompt_label.setText(
                f"<b>Creation Prompt</b> ({escape(timestamp)})<br>{escape(creation_prompt_text)}{meta_html}"
            )
            self.use_template_btn.show()
        else:
            self.creation_prompt_label.setText(
                f"<b>Source File:</b> {escape(os.path.basename(path))}"
            )
            self.use_template_btn.hide()

        if ext in video_extensions:
            self.video_widget.set_prompt_text(creation_prompt_text)
        else:
            self.video_widget.set_prompt_text(None)

        input_generations = self.db.query(
            Generation,
            lambda g: (g.input_asset1_id == asset_id)
            or (g.input_asset2_id == asset_id),
        )
        history_items = []
        for gen in input_generations:
            prompt_text = escape(gen.prompt or "No prompt provided")
            timestamp = (
                gen.created_at.strftime("%Y-%m-%d %H:%M")
                if getattr(gen, "created_at", None)
                else "Unknown time"
            )
            roles = []
            if gen.input_asset1_id == asset_id:
                roles.append("Input 1")
            if gen.input_asset2_id == asset_id:
                roles.append("Input 2")
            settings = gen.settings or {}
            details = []
            model = settings.get("model")
            if model:
                details.append(f"Model: {model}")
            quality = settings.get("quality")
            if quality:
                details.append(f"Quality: {quality}")
            duration = settings.get("duration")
            if duration:
                details.append(f"Duration: {duration}s")
            camera = settings.get("camera_movement")
            if camera and camera != "None":
                details.append(f"Camera: {camera}")
            meta_parts = []
            if roles:
                meta_parts.append(", ".join(roles))
            meta_parts.extend(details)
            meta_html = (
                f"<span style='color:#bbb;'> ({escape(' - '.join(meta_parts))})</span>"
                if meta_parts
                else ""
            )
            history_items.append(
                f"<li><strong>{escape(timestamp)}</strong> - {prompt_text}{meta_html}</li>"
            )

        history_html = (
            "<ul>" + "".join(history_items) + "</ul>"
            if history_items
            else "Not used as an input yet."
        )
        self.prompt_history_view.setHtml(history_html)

        has_generation = bool(creation_generations)
        if has_generation and self.asset_service and os.path.exists(path):
            self.delete_btn.show()
        else:
            self.delete_btn.hide()

        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.asset_list) - 1)

    def _delete_current_asset(self) -> None:
        if not self.asset_service or not self.asset_list:
            return

        asset_data = self.asset_list[self.current_index]
        path = asset_data.get("path")
        if not path:
            return

        reply = QMessageBox.question(
            self,
            "Delete Asset",
            f"Are you sure you want to delete '{os.path.basename(path)}'? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.media_player.stop()
        try:
            self.asset_service.delete_asset_by_path(path)
        except Exception as exc:
            QMessageBox.critical(self, "Delete Asset", f"Failed to delete asset: {exc}")
            self.log.error("Failed to delete asset %s: %s", path, exc, exc_info=True)
            return

        self.close()

    def show_previous(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.load_asset()

    def show_next(self):
        if self.current_index < len(self.asset_list) - 1:
            self.current_index += 1
            self.load_asset()

    def closeEvent(self, event):
        self.media_player.stop()
        super().closeEvent(event)

    def _on_use_as_template(self):
        if self.creation_prompt:
            asset_data = self.asset_list[self.current_index]
            self.events.publish(
                "generator:use_template",
                asset_path=asset_data["path"],
                prompt=self.creation_prompt,
            )
            self.log.notification(
                f"Loaded template from '{os.path.basename(asset_data['path'])}'."
            )
            self.close()
