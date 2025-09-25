"""
Timeline Widget

Interactive timeline for controlling scene animation and setting keyframes for visual tags.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel, QPushButton,
    QSpinBox, QDoubleSpinBox, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QPaintEvent

from ..models.scene_graph import Scene
from ..models.visual_tag import VisualTag, AnimationCurve, Keyframe
from framework.modern_ui import apply_modern_style


class TimelineRuler(QWidget):
    """Timeline ruler showing time markers and current playhead position"""

    time_clicked = pyqtSignal(float)  # time_position
    playhead_moved = pyqtSignal(float)  # time_position

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 5.0  # Default 5 seconds
        self.current_time = 0.0
        self.scale = 100  # pixels per second
        self.dragging_playhead = False

        # Visual settings
        self.ruler_height = 30
        self.playhead_color = QColor("#007bff")
        self.tick_color = QColor("#666666")
        self.background_color = QColor("#f8f9fa")

        self.setFixedHeight(self.ruler_height)
        self.setMouseTracking(True)

    def set_duration(self, duration: float):
        """Set the timeline duration"""
        self.duration = max(0.1, duration)
        self.update()

    def set_current_time(self, time: float):
        """Set the current playhead position"""
        self.current_time = max(0, min(time, self.duration))
        self.update()

    def set_scale(self, scale: float):
        """Set the timeline scale (pixels per second)"""
        self.scale = max(10, min(500, scale))
        self.update()

    def time_to_pixel(self, time: float) -> int:
        """Convert time to pixel position"""
        return int(time * self.scale)

    def pixel_to_time(self, pixel: int) -> float:
        """Convert pixel position to time"""
        return pixel / self.scale

    def paintEvent(self, event: QPaintEvent):
        """Paint the timeline ruler"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear background
        painter.fillRect(self.rect(), self.background_color)

        # Draw time ticks
        painter.setPen(QPen(self.tick_color, 1))

        # Major ticks (seconds)
        for i in range(int(self.duration) + 1):
            x = self.time_to_pixel(i)
            painter.drawLine(x, 0, x, self.ruler_height // 2)

            # Time labels
            painter.setPen(QPen(QColor("#333333")))
            painter.setFont(QFont("", 8))
            painter.drawText(x + 2, self.ruler_height // 2 + 12, f"{i}s")
            painter.setPen(QPen(self.tick_color, 1))

        # Minor ticks (0.5 seconds)
        for i in range(int(self.duration * 2)):
            time = i * 0.5
            if time != int(time):  # Skip major ticks
                x = self.time_to_pixel(time)
                painter.drawLine(x, 0, x, self.ruler_height // 4)

        # Draw playhead
        playhead_x = self.time_to_pixel(self.current_time)
        painter.setPen(QPen(self.playhead_color, 2))
        painter.drawLine(playhead_x, 0, playhead_x, self.ruler_height)

        # Draw playhead handle
        painter.setBrush(QBrush(self.playhead_color))
        painter.setPen(QPen(self.playhead_color.darker(), 1))
        handle_rect = QRect(playhead_x - 4, 0, 8, 12)
        painter.drawRoundedRect(handle_rect, 2, 2)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for playhead dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            time = self.pixel_to_time(event.position().x())
            playhead_x = self.time_to_pixel(self.current_time)

            # Check if clicking near playhead
            if abs(event.position().x() - playhead_x) < 8:
                self.dragging_playhead = True
            else:
                # Click to set time
                self.current_time = max(0, min(time, self.duration))
                self.time_clicked.emit(self.current_time)
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for playhead dragging"""
        if self.dragging_playhead:
            time = self.pixel_to_time(event.position().x())
            self.current_time = max(0, min(time, self.duration))
            self.playhead_moved.emit(self.current_time)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_playhead = False


class KeyframeTrack(QWidget):
    """Track widget showing keyframes for a specific property"""

    keyframe_added = pyqtSignal(str, float, object)  # property_name, time, value
    keyframe_removed = pyqtSignal(str, float)  # property_name, time
    keyframe_selected = pyqtSignal(str, float)  # property_name, time

    def __init__(self, property_name: str, tag_id: str, parent=None):
        super().__init__(parent)
        self.property_name = property_name
        self.tag_id = tag_id
        self.keyframes = []  # List of (time, value) tuples
        self.selected_keyframe = None
        self.scale = 100  # pixels per second
        self.duration = 5.0

        # Visual settings
        self.track_height = 24
        self.keyframe_color = QColor("#28a745")
        self.selected_color = QColor("#ffc107")

        self.setFixedHeight(self.track_height)
        self.setMouseTracking(True)

    def set_keyframes(self, keyframes):
        """Set the keyframes for this track"""
        self.keyframes = keyframes
        self.update()

    def set_scale(self, scale: float):
        """Set the timeline scale"""
        self.scale = scale
        self.update()

    def set_duration(self, duration: float):
        """Set the timeline duration"""
        self.duration = duration
        self.update()

    def time_to_pixel(self, time: float) -> int:
        """Convert time to pixel position"""
        return int(time * self.scale)

    def pixel_to_time(self, pixel: int) -> float:
        """Convert pixel position to time"""
        return pixel / self.scale

    def paintEvent(self, event: QPaintEvent):
        """Paint the keyframe track"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear background
        painter.fillRect(self.rect(), QColor("#ffffff"))

        # Draw track line
        painter.setPen(QPen(QColor("#dee2e6"), 1))
        painter.drawLine(0, self.track_height // 2, self.width(), self.track_height // 2)

        # Draw keyframes
        for time, value in self.keyframes:
            x = self.time_to_pixel(time)
            is_selected = self.selected_keyframe == time

            color = self.selected_color if is_selected else self.keyframe_color
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(), 1))

            # Draw keyframe diamond
            points = [
                QPoint(x, self.track_height // 2 - 6),  # top
                QPoint(x + 6, self.track_height // 2),  # right
                QPoint(x, self.track_height // 2 + 6),  # bottom
                QPoint(x - 6, self.track_height // 2)   # left
            ]
            painter.drawPolygon(points)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for keyframe selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            click_time = self.pixel_to_time(event.position().x())

            # Find nearest keyframe
            nearest_keyframe = None
            nearest_distance = float('inf')

            for time, value in self.keyframes:
                distance = abs(time - click_time)
                if distance < nearest_distance and distance < 0.1:  # 0.1 second tolerance
                    nearest_distance = distance
                    nearest_keyframe = time

            if nearest_keyframe is not None:
                self.selected_keyframe = nearest_keyframe
                self.keyframe_selected.emit(self.property_name, nearest_keyframe)
                self.update()
            else:
                # Add new keyframe at click position
                self.keyframe_added.emit(self.property_name, click_time, 0.0)  # Default value

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to remove keyframe"""
        click_time = self.pixel_to_time(event.position().x())

        # Find keyframe to remove
        for time, value in self.keyframes:
            if abs(time - click_time) < 0.1:
                self.keyframe_removed.emit(self.property_name, time)
                break


class TimelineWidget(QWidget):
    """Main timeline widget with playback controls and keyframe tracks"""

    time_changed = pyqtSignal(float)  # current_time
    keyframe_modified = pyqtSignal(str, str, float, object)  # tag_id, property, time, value
    playback_toggled = pyqtSignal(bool)  # is_playing

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.theme_manager = framework.get_service("theme_manager")

        # Timeline state
        self.scene: Scene = None
        self.current_time = 0.0
        self.duration = 5.0
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._advance_playhead)

        # Keyframe tracks
        self.keyframe_tracks = {}  # tag_id -> {property_name -> KeyframeTrack}

        self._init_ui()
        self._connect_signals()
        self._apply_modern_styling()

    def _init_ui(self):
        """Initialize the timeline UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Timeline header with playback controls
        header_layout = QHBoxLayout()

        # Play/Pause button
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(32, 32)
        self.play_button.setToolTip("Play/Pause")
        header_layout.addWidget(self.play_button)

        # Stop button
        self.stop_button = QPushButton("⏹")
        self.stop_button.setFixedSize(32, 32)
        self.stop_button.setToolTip("Stop")
        header_layout.addWidget(self.stop_button)

        header_layout.addSpacing(10)

        # Time display
        self.time_label = QLabel("00:00")
        self.time_label.setFont(QFont("monospace", 10))
        header_layout.addWidget(self.time_label)

        header_layout.addSpacing(10)

        # Duration control
        header_layout.addWidget(QLabel("Duration:"))
        self.duration_spinbox = QDoubleSpinBox()
        self.duration_spinbox.setRange(0.1, 60.0)
        self.duration_spinbox.setValue(self.duration)
        self.duration_spinbox.setSuffix("s")
        self.duration_spinbox.setFixedWidth(80)
        header_layout.addWidget(self.duration_spinbox)

        header_layout.addSpacing(10)

        # Timeline scale control
        header_layout.addWidget(QLabel("Zoom:"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 500)
        self.scale_slider.setValue(100)
        self.scale_slider.setFixedWidth(100)
        header_layout.addWidget(self.scale_slider)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Timeline ruler
        self.ruler = TimelineRuler()
        main_layout.addWidget(self.ruler)

        # Scroll area for keyframe tracks
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(100)

        # Container for keyframe tracks
        self.tracks_container = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_layout.setSpacing(2)

        scroll_area.setWidget(self.tracks_container)
        main_layout.addWidget(scroll_area, 1)

        # Add placeholder message
        self.placeholder_label = QLabel("No scene loaded\n\nLoad a scene to see animation tracks")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #6c757d; font-style: italic; padding: 20px;")
        self.tracks_layout.addWidget(self.placeholder_label)
        self.tracks_layout.addStretch()

    def _connect_signals(self):
        """Connect timeline signals"""
        self.play_button.clicked.connect(self._toggle_playback)
        self.stop_button.clicked.connect(self._stop_playback)
        self.duration_spinbox.valueChanged.connect(self._update_duration)
        self.scale_slider.valueChanged.connect(self._update_scale)
        self.ruler.time_clicked.connect(self._set_current_time)
        self.ruler.playhead_moved.connect(self._set_current_time)

    def _apply_modern_styling(self):
        """Apply modern styling to the timeline"""
        if self.theme_manager:
            apply_modern_style(self, self.theme_manager, "card")

    def set_scene(self, scene: Scene):
        """Set the scene to display timeline for"""
        self.scene = scene
        if scene:
            self.duration = scene.duration
            self.duration_spinbox.setValue(self.duration)
            self.ruler.set_duration(self.duration)
            self._rebuild_keyframe_tracks()
            self.placeholder_label.setVisible(False)
        else:
            self._clear_keyframe_tracks()
            self.placeholder_label.setVisible(True)

    def _rebuild_keyframe_tracks(self):
        """Rebuild keyframe tracks for current scene"""
        self._clear_keyframe_tracks()

        if not self.scene:
            return

        # Create tracks for each tag and its animatable properties
        for tag in self.scene.visual_tags.values():
            self._add_tag_tracks(tag)

    def _add_tag_tracks(self, tag: VisualTag):
        """Add keyframe tracks for a specific tag"""
        animatable_properties = [
            "position.x", "position.y", "position.z",
            "rotation.x", "rotation.y", "rotation.z",
            "scale.x", "scale.y", "scale.z",
            "opacity", "visibility"
        ]

        tag_tracks = {}

        for prop_name in animatable_properties:
            # Create track header
            track_header = QLabel(f"{tag.name or tag.id[:8]}.{prop_name}")
            track_header.setFixedWidth(150)
            track_header.setStyleSheet("background: #f8f9fa; padding: 4px; border-right: 1px solid #dee2e6;")

            # Create keyframe track
            track = KeyframeTrack(prop_name, tag.id)
            track.set_scale(self.scale_slider.value())
            track.set_duration(self.duration)

            # Load existing keyframes
            keyframes = []
            for animation in tag.animations:
                if animation.property_path == prop_name:
                    keyframes = [(kf.time, kf.value) for kf in animation.keyframes]
                    break
            track.set_keyframes(keyframes)

            # Connect track signals
            track.keyframe_added.connect(self._on_keyframe_added)
            track.keyframe_removed.connect(self._on_keyframe_removed)
            track.keyframe_selected.connect(self._on_keyframe_selected)

            # Create track row layout
            track_layout = QHBoxLayout()
            track_layout.setContentsMargins(0, 0, 0, 0)
            track_layout.addWidget(track_header)
            track_layout.addWidget(track, 1)

            # Add to tracks layout
            track_widget = QWidget()
            track_widget.setLayout(track_layout)
            track_widget.setFixedHeight(24)
            self.tracks_layout.insertWidget(self.tracks_layout.count() - 1, track_widget)

            tag_tracks[prop_name] = track

        self.keyframe_tracks[tag.id] = tag_tracks

    def _clear_keyframe_tracks(self):
        """Clear all keyframe tracks"""
        # Remove all track widgets except placeholder and stretch
        while self.tracks_layout.count() > 2:
            child = self.tracks_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.keyframe_tracks.clear()

    def _toggle_playback(self):
        """Toggle timeline playback"""
        self.is_playing = not self.is_playing

        if self.is_playing:
            self.play_button.setText("⏸")
            self.playback_timer.start(16)  # ~60 FPS
        else:
            self.play_button.setText("▶")
            self.playback_timer.stop()

        self.playback_toggled.emit(self.is_playing)

    def _stop_playback(self):
        """Stop timeline playback and reset to beginning"""
        self.is_playing = False
        self.play_button.setText("▶")
        self.playback_timer.stop()
        self._set_current_time(0.0)

    def _advance_playhead(self):
        """Advance playhead during playback"""
        if self.is_playing:
            self.current_time += 0.016  # 16ms step

            if self.current_time >= self.duration:
                self.current_time = self.duration
                self._stop_playback()

            self._update_time_display()
            self.ruler.set_current_time(self.current_time)
            self.time_changed.emit(self.current_time)

    def _set_current_time(self, time: float):
        """Set current timeline position"""
        self.current_time = max(0, min(time, self.duration))
        self._update_time_display()
        self.ruler.set_current_time(self.current_time)
        self.time_changed.emit(self.current_time)

    def _update_time_display(self):
        """Update time display label"""
        minutes = int(self.current_time // 60)
        seconds = int(self.current_time % 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _update_duration(self, duration: float):
        """Update timeline duration"""
        self.duration = duration
        self.ruler.set_duration(duration)

        # Update all tracks
        for tag_tracks in self.keyframe_tracks.values():
            for track in tag_tracks.values():
                track.set_duration(duration)

        # Update scene if available
        if self.scene:
            self.scene.duration = duration

    def _update_scale(self, scale: int):
        """Update timeline zoom scale"""
        self.ruler.set_scale(scale)

        # Update all tracks
        for tag_tracks in self.keyframe_tracks.values():
            for track in tag_tracks.values():
                track.set_scale(scale)

    def _on_keyframe_added(self, property_name: str, time: float, value):
        """Handle keyframe addition"""
        # Find the tag this track belongs to
        for tag_id, tag_tracks in self.keyframe_tracks.items():
            if property_name in tag_tracks:
                self.keyframe_modified.emit(tag_id, property_name, time, value)
                break

    def _on_keyframe_removed(self, property_name: str, time: float):
        """Handle keyframe removal"""
        for tag_id, tag_tracks in self.keyframe_tracks.items():
            if property_name in tag_tracks:
                # Signal removal with None value
                self.keyframe_modified.emit(tag_id, property_name, time, None)
                break

    def _on_keyframe_selected(self, property_name: str, time: float):
        """Handle keyframe selection"""
        self.log.debug(f"Keyframe selected: {property_name} at {time}s")

    def refresh_tracks(self):
        """Refresh all keyframe tracks"""
        if self.scene:
            self._rebuild_keyframe_tracks()