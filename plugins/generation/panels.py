# D:/My Drive/code/pixmotion/plugins/generation/panels.py
import os
import tempfile
import uuid
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                             QTextEdit, QComboBox, QLineEdit, QPushButton, QFormLayout,
                             QTabWidget, QSplitter, QApplication, QMenu, QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QPainter, QColor, QCursor, QImage
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget

from core.models import Asset


class AspectLockedVideoWidget(QVideoWidget):
    """A QVideoWidget that maintains aspect ratio and properly handles drag-and-drop."""
    dropped = pyqtSignal(QMimeData)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        # We let the layout handle the size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def dragEnterEvent(self, event: 'QDragEnterEvent'):
        """Accepts drops that have URLs or text."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: 'QDropEvent'):
        """Emits a signal with the mime data when an item is dropped."""
        self.dropped.emit(event.mimeData())


class ImageDisplayWidget(QWidget):
    """A simple widget that paints a pixmap, scaled to fit, without affecting layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._placeholder_text = ""

    def set_pixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()  # Schedule a repaint

    def set_placeholder_text(self, text):
        self._placeholder_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._pixmap and not self._pixmap.isNull():
            scaled_pixmap = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            painter.setPen(QColor(180, 180, 180))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._placeholder_text)


class VideoPlayerWidget(QFrame):
    """A widget that can display a thumbnail or a placeholder."""
    asset_dropped = pyqtSignal(str)

    def __init__(self, title, framework, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.title = title
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.db = framework.get_service("database_service")
        self.asset_path = None
        self.is_video = False
        self._original_pixmap = None  # To store the unscaled pixmap
        self._temp_frame_path = None  # To store path of extracted frame

        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        # Stack for showing image or video
        self.media_stack = QStackedWidget()
        self.image_display = ImageDisplayWidget()
        self.image_display.set_placeholder_text(f"{self.title}\n\nDrop Asset Here")

        # --- Use a layout to manage the video widget's position and aspect ratio ---
        video_container = QWidget()
        video_layout = QHBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_widget = AspectLockedVideoWidget()
        video_layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer()
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.video_widget.dropped.connect(self._handle_drop_event)  # Connect to the video widget's drop signal

        self.media_stack.addWidget(self.image_display)
        self.media_stack.addWidget(video_container)  # Add the container, not the widget directly
        main_layout.addWidget(self.media_stack)

        # Clear button overlay
        self.clear_btn = QPushButton("X", self)
        self.clear_btn.setFixedSize(20, 20)
        self.clear_btn.setStyleSheet("background-color: rgba(44, 44, 44, 180); border-radius: 10px; font-weight: bold;")
        self.clear_btn.clicked.connect(self.clear_asset)
        self.clear_btn.hide()

        # Controls
        self.controls_widget = QWidget()
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        self.play_pause_btn = QPushButton("▶ Play")
        self.play_pause_btn.clicked.connect(self._toggle_playback)
        controls_layout.addStretch()
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addStretch()
        main_layout.addWidget(self.controls_widget)
        self.controls_widget.hide()  # Hide by default

    def set_asset(self, asset_path):
        self.asset_path = asset_path  # Store original path
        if self._temp_frame_path and os.path.exists(self._temp_frame_path):
            try:
                os.remove(self._temp_frame_path)
            except OSError as e:
                self.log.warning(f"Could not remove temp frame: {e}")
            self._temp_frame_path = None

        if not asset_path:
            self.clear_asset()
            self.clear_btn.hide()
            return

        _, ext = os.path.splitext(asset_path.lower())
        self.is_video = ext in ['.mp4', '.mov', '.avi']

        if self.is_video:
            self._original_pixmap = None  # Clear pixmap if it's a video
            self.media_player.setSource(QUrl.fromLocalFile(asset_path))
            self.media_stack.setCurrentIndex(1)  # Show video container
            self.controls_widget.show()
            self.play_pause_btn.setText("▶ Play")
            self.clear_btn.show()
        else:  # It's an image
            pixmap_path = self._get_thumbnail_path(asset_path)
            if not pixmap_path or not os.path.exists(pixmap_path):
                pixmap_path = asset_path

            if pixmap_path and os.path.exists(pixmap_path):
                # Store the original, unscaled pixmap
                self._original_pixmap = QPixmap(pixmap_path)  # This is the source of truth
                self.image_display.set_pixmap(self._original_pixmap)
            else:
                self._original_pixmap = None
            self.media_stack.setCurrentIndex(0)  # Show image display
            self.controls_widget.hide()
            self.media_player.setSource(QUrl())
            self.clear_btn.show()

    def resizeEvent(self, event):
        """Handle resizing of the container to position overlay widgets."""
        super().resizeEvent(event)
        # Position clear button
        self.clear_btn.move(self.width() - self.clear_btn.width() - 3, 3)
        # The image display will repaint itself automatically.
        # The video widget's layout will handle its resizing and positioning.

    def _get_thumbnail_path(self, original_path):
        """Helper to find the thumbnail for a given original asset path."""
        if self.db:
            assets = self.db.query(Asset, lambda a: a.path == original_path)
            if assets:
                return assets[0].thumbnail_path
        return None

    def clear_asset(self):
        self.asset_path = None
        self.is_video = False
        self._original_pixmap = None
        self.media_player.setSource(QUrl())
        self.image_display.set_placeholder_text(f"{self.title}\n\nDrop Asset Here")
        self.image_display.set_pixmap(None)
        self.media_stack.setCurrentIndex(0)  # Show image display
        self.clear_btn.hide()
        self.controls_widget.hide()

    def dragEnterEvent(self, event):
        self.log.info(f"[VideoPlayerWidget.dragEnterEvent] MimeData formats: {event.mimeData().formats()}")
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handles drops directly on the QFrame (the placeholder area)."""
        self._handle_drop_event(event.mimeData())

    def _handle_drop_event(self, mime_data: QMimeData):
        """Centralized logic to process mime data from a drop."""
        self.log.info("[VideoPlayerWidget._handle_drop_event] Drop event received.")
        path = None
        if mime_data.hasUrls():
            url = mime_data.urls()[0]
            self.log.info(f"[VideoPlayerWidget.dropEvent] Dropped URL: {url.toString()}")
            if url.isLocalFile():
                path = url.toLocalFile()
        elif mime_data.hasText():
            path = mime_data.text()
            self.log.info(f"[VideoPlayerWidget.dropEvent] Dropped Text: {path}")

        if path and os.path.exists(path):
            self.log.info(f"[VideoPlayerWidget.dropEvent] Emitting asset_dropped with path: {path}")
            self.asset_dropped.emit(path)
        else:
            self.log.warning(f"[VideoPlayerWidget.dropEvent] Path not valid or does not exist: {path}")

    def contextMenuEvent(self, event):
        self._show_context_menu()

    def _show_context_menu(self):
        """Creates and shows the context menu."""
        context_menu = QMenu(self)
        paste_action = context_menu.addAction("Paste from Clipboard")
        paste_action.triggered.connect(self._paste_from_clipboard)
        context_menu.exec(QCursor.pos())

    def _paste_from_clipboard(self):
        """Executes the main paste command and updates the widget if successful."""
        command_manager = self.framework.get_service("command_manager")
        if not command_manager:
            self.log.error("CommandManager not available for paste operation.")
            return

        # Execute the command and get the new asset object back
        new_asset = command_manager.execute("assets.paste_from_clipboard")

        if new_asset and hasattr(new_asset, 'path'):
            # The command was successful, update the widget with the new asset's path
            self.log.info(f"Pasted asset created: {new_asset.path}")
            self.asset_dropped.emit(new_asset.path)
        else:
            self.log.info("Paste command executed but returned no new asset.")

    def _toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_pause_btn.setText("▶ Play")
        else:
            self.media_player.play()
            self.play_pause_btn.setText("❚❚ Pause")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # This is now handled by setLoops(Infinite), but we keep it for safety
            self.play_pause_btn.setText("▶ Play")
            self.media_player.setPosition(0)

    def get_frame_for_generation(self) -> str | None:
        """
        Returns the path of the asset to be used for generation.
        If it's an image, returns its path.
        If it's a video, extracts the current frame and returns the path to the temp file.
        """
        if not self.asset_path:
            return None

        if not self.is_video:
            return self.asset_path

        # It's a video, so we need to extract a frame.
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()  # Pause it to grab a stable frame
            self.play_pause_btn.setText("▶ Play")

        video_frame = self.video_widget.videoSink().videoFrame()
        if not video_frame.isValid():
            self.log.error("Could not get a valid video frame to generate from.")
            return None

        image: QImage = video_frame.toImage()
        if image.isNull():
            self.log.error("Failed to convert video frame to image.")
            return None

        self._temp_frame_path = os.path.join(tempfile.gettempdir(), f"pixmotion_frame_{uuid.uuid4().hex}.png")
        image.save(self._temp_frame_path, "PNG")
        self.log.info(f"Extracted video frame for generation: {self._temp_frame_path}")
        return self._temp_frame_path


class PromptTextEdit(QTextEdit):
    """A QTextEdit that accepts drag-and-drop for asset paths."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                filename = os.path.basename(url.toLocalFile())
                prompt_text = os.path.splitext(filename)[0]
                self.insertPlainText(prompt_text)


class GeneratorPanel(QWidget):
    """A consolidated, well-organized panel for all generation controls."""

    def __init__(self, framework):
        super().__init__()
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.settings = framework.get_service("settings_service")
        self.db = framework.get_service("database_service")
        self.asset_service = framework.get_service("asset_service")
        self.events = framework.get_service("event_manager")
        self._init_ui()
        self.connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        inputs_layout = QHBoxLayout()
        self.input1 = VideoPlayerWidget("Input 1", self.framework)
        self.input2 = VideoPlayerWidget("Input 2", self.framework)
        inputs_layout.addWidget(self.input1)
        inputs_layout.addWidget(self.input2)

        controls_splitter = QSplitter(Qt.Orientation.Vertical)

        self.prompt_edit = PromptTextEdit()
        self.prompt_edit.setPlaceholderText("Enter prompt or drop an asset...")
        controls_splitter.addWidget(self.prompt_edit)

        tabs = QTabWidget()
        settings_widget = QWidget()
        advanced_widget = QWidget()
        tabs.addTab(settings_widget, "Settings")
        tabs.addTab(advanced_widget, "Advanced")
        controls_splitter.addWidget(tabs)

        controls_splitter.setSizes([200, 150])

        settings_layout = QFormLayout(settings_widget)
        settings_layout.setSpacing(5)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Optional filename for generated video")

        self.model_combo = QComboBox()
        self.model_combo.addItems(["v5", "v4.5", "v4", "v3.5"])
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["360p", "540p", "720p", "1080p"])
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["5", "8"])
        settings_layout.addRow("Title:", self.title_edit)
        settings_layout.addRow("Model:", self.model_combo)
        settings_layout.addRow("Quality:", self.quality_combo)
        settings_layout.addRow("Duration:", self.duration_combo)

        advanced_layout = QFormLayout(advanced_widget)
        advanced_layout.setSpacing(5)
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["None", "zoom_in", "zoom_out", "pan_left", "pan_right"])
        self.style_combo = QComboBox()
        self.style_combo.addItems(["None", "anime", "3d_animation", "cyberpunk", "comic"])
        self.motion_combo = QComboBox()
        self.motion_combo.addItems(["normal", "fast"])
        self.seed_edit = QLineEdit()
        self.negative_prompt_edit = QLineEdit()
        advanced_layout.addRow("Camera:", self.camera_combo)
        advanced_layout.addRow("Style:", self.style_combo)
        advanced_layout.addRow("Motion:", self.motion_combo)
        advanced_layout.addRow("Seed:", self.seed_edit)
        advanced_layout.addRow("Negative Prompt:", self.negative_prompt_edit)

        buttons_layout = QHBoxLayout()
        self.basic_generate_btn = QPushButton("Generate from Input 1")
        self.transition_generate_btn = QPushButton("Create Transition")
        buttons_layout.addWidget(self.basic_generate_btn)
        buttons_layout.addWidget(self.transition_generate_btn)

        main_layout.addLayout(inputs_layout, stretch=1)
        main_layout.addWidget(controls_splitter, stretch=2)
        main_layout.addLayout(buttons_layout)

    def connect_signals(self):
        self.basic_generate_btn.clicked.connect(self._on_basic_generate)
        self.transition_generate_btn.clicked.connect(self._on_transition_generate)
        self.input1.asset_dropped.connect(self._on_asset_dropped_input1)
        self.input2.asset_dropped.connect(self._on_asset_dropped_input2)
        self.events.subscribe("preview:send_to_input", self._on_send_to_input)
        self.events.subscribe("generator:use_template", self._on_use_template)

    def _on_send_to_input(self, event_data):
        """Unpacks the event data tuple and updates the correct input."""
        event_name, data = event_data
        target = data.get("target")
        path = data.get("path")
        if target == 1:
            self.input1.set_asset(path)
        elif target == 2:
            self.input2.set_asset(path)

    def _on_asset_dropped_input1(self, original_path):
        self.input1.set_asset(original_path)
        self.log.info(f"Asset dropped on Input 1: {original_path}")

    def _on_asset_dropped_input2(self, original_path):
        self.input2.set_asset(original_path)
        self.log.info(f"Asset dropped on Input 2: {original_path}")

    def save_state(self):
        """Gathers the current state of all widgets into a dictionary for persistence."""
        state = {
            "title": self.title_edit.text(),
            "prompt": self.prompt_edit.toPlainText(),
            "input_asset1_id": self._ensure_asset_and_get_id(self.input1.get_frame_for_generation()),
            "input_asset2_id": self._ensure_asset_and_get_id(self.input2.get_frame_for_generation()),
            "model": self.model_combo.currentText(),
            "quality": self.quality_combo.currentText(),
            "duration": int(self.duration_combo.currentText()),
            "camera_movement": self.camera_combo.currentText() if self.camera_combo.currentIndex() > 0 else "None",
            "style": self.style_combo.currentText() if self.style_combo.currentIndex() > 0 else "None",
            "motion_mode": self.motion_combo.currentText(),
            "seed": self.seed_edit.text() or None,
            "negative_prompt": self.negative_prompt_edit.text() or None
        }
        return state

    def restore_state(self, state: dict):
        """Restores the state of all widgets from a dictionary."""
        self.log.info("Restoring GeneratorPanel state...")
        self.title_edit.setText(state.get("title", ""))
        self.prompt_edit.setPlainText(state.get("prompt", ""))
        self.model_combo.setCurrentText(state.get("model", "v5"))
        self.quality_combo.setCurrentText(state.get("quality", "360p"))
        self.duration_combo.setCurrentText(str(state.get("duration", "5")))
        self.camera_combo.setCurrentText(state.get("camera_movement", "None"))
        self.style_combo.setCurrentText(state.get("style", "None"))
        self.motion_combo.setCurrentText(state.get("motion_mode", "normal"))
        self.seed_edit.setText(state.get("seed", ""))
        self.negative_prompt_edit.setText(state.get("negative_prompt", ""))

        # Restore assets by finding their paths from the saved IDs
        if state.get("input_asset1_id"):
            self.input1.set_asset(self._get_path_from_asset_id(state["input_asset1_id"]))
        if state.get("input_asset2_id"):
            self.input2.set_asset(self._get_path_from_asset_id(state["input_asset2_id"]))

    def _on_use_template(self, **kwargs):
        """Sets the generator panel's state from a template."""
        asset_path = kwargs.get("asset_path")
        prompt = kwargs.get("prompt")
        if asset_path:
            self.input1.set_asset(asset_path)
        if prompt:
            self.prompt_edit.setPlainText(prompt)

    def _on_basic_generate(self):
        """Triggers a generation using only Input 1."""
        settings = self.save_state()
        settings["input_asset2_id"] = None  # Ensure input 2 is ignored

        if not settings["prompt"] or not settings["input_asset1_id"]:
            self.log.notification("Prompt and Input 1 are required for basic generation.")
            return

        self.framework.get_service("command_manager").execute(
            "story.generate_video",
            **settings  # Unpack the dictionary as keyword arguments
        )

    def _on_transition_generate(self):
        """Triggers a generation using both Input 1 and Input 2."""
        settings = self.save_state()

        if not settings["prompt"] or not settings["input_asset1_id"] or not settings["input_asset2_id"]:
            self.log.notification("Prompt, Input 1, and Input 2 are required for transitions.")
            return

        self.framework.get_service("command_manager").execute(
            "story.generate_video",
            **settings
        )

    def _ensure_asset_and_get_id(self, path: str) -> str | None:
        """
        Ensures an asset exists in the database for the given path and returns its ID.
        If the asset doesn't exist, it's created.
        """
        if not path: return None
        if not self.asset_service:
            self.log.error("AssetService not available. Cannot ensure asset exists.")
            return None
        # add_asset is idempotent: it creates the asset if it's new, or just returns it if it exists.
        asset_obj = self.asset_service.add_asset(path)
        return asset_obj.id if asset_obj else None

    def _get_path_from_asset_id(self, asset_id: str) -> str | None:
        """Finds the file path for a given asset ID."""
        if not asset_id: return None
        if not self.asset_service: return None
        # Use the service to get the path, which is more robust.
        return self.asset_service.get_asset_path(asset_id)