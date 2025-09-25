"""
Canvas Widget

Interactive canvas for visual scene composition where users can place and manipulate visual tags.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QPaintEvent, QPixmap

from ..models.scene_graph import Scene
from ..models.visual_tag import VisualTag, ElementType
from framework.modern_ui import apply_modern_style


class CanvasWidget(QWidget):
    """Interactive canvas for visual composition"""

    # Signals
    tag_selected = pyqtSignal(str)  # tag_id
    tag_moved = pyqtSignal(str, float, float)  # tag_id, x, y
    tag_double_clicked = pyqtSignal(str)  # tag_id

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.theme_manager = framework.get_service("theme_manager")
        self.composer_service = None

        # Canvas state
        self.scene: Scene = None
        self.selected_tag_id: str = None
        self.dragging_tag: str = None
        self.last_mouse_pos: QPoint = QPoint()

        # Canvas properties
        self.canvas_scale = 1.0
        self.canvas_offset = QPoint(0, 0)
        self.show_grid = True
        self.grid_size = 50

        # Visual settings
        self.tag_size = 60
        self.selection_width = 3

        self._init_ui()

    def _init_ui(self):
        """Initialize the canvas UI"""
        # Set minimum size
        self.setMinimumSize(400, 300)

        # Enable mouse tracking
        self.setMouseTracking(True)

        # Apply styling
        if self.theme_manager:
            apply_modern_style(self, self.theme_manager, "card")

        # Set background
        self.setStyleSheet(self.styleSheet() + """
            CanvasWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)

    def set_scene(self, scene: Scene):
        """Set the scene to display"""
        self.scene = scene
        self.selected_tag_id = None

        # Get composer service reference if needed
        if not self.composer_service:
            try:
                self.composer_service = self.framework.get_service("visual_composer_service")
            except:
                pass

        self.update()
        self.log.debug(f"Canvas set to scene: {scene.name if scene else 'None'}")

    def refresh(self):
        """Refresh the canvas display"""
        self.update()

    def paintEvent(self, event: QPaintEvent):
        """Paint the canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear background
        painter.fillRect(self.rect(), QColor("#f8f9fa"))

        # Draw background image/video if available
        if self.scene and self.scene.background_asset_id:
            self._draw_background(painter)

        # Draw grid if enabled
        if self.show_grid:
            self._draw_grid(painter)

        # Draw scene if available
        if self.scene:
            self._draw_scene(painter)
        else:
            self._draw_empty_state(painter)

    def _draw_background(self, painter: QPainter):
        """Draw background image or video frame"""
        try:
            if not self.scene or not self.scene.background_asset_id:
                return

            # Get asset service to load background media
            asset_service = self.framework.get_service("asset_service")
            if not asset_service:
                return

            # Try to get asset path (this is a simplified approach)
            # You may need to adjust based on your actual asset service API
            background_path = None

            try:
                # Attempt to get asset information
                if hasattr(asset_service, 'get_asset_by_id'):
                    asset = asset_service.get_asset_by_id(self.scene.background_asset_id)
                    if asset:
                        background_path = asset.get('path')
                elif hasattr(asset_service, 'get_asset_path'):
                    background_path = asset_service.get_asset_path(self.scene.background_asset_id)
            except:
                # Fallback: use asset ID as path (for demo purposes)
                if self.scene.background_asset_id.startswith('/') or self.scene.background_asset_id.startswith('C:'):
                    background_path = self.scene.background_asset_id

            if not background_path:
                return

            # Load and draw image
            background_type = self.scene.background_type or ""
            if background_type.lower() in ["image", "jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                pixmap = QPixmap(background_path)
                if not pixmap.isNull():
                    # Calculate scaled size
                    canvas_rect = self.rect()
                    scale = self.scene.background_scale
                    scaled_size = pixmap.size() * scale

                    # Center the background
                    x = (canvas_rect.width() - scaled_size.width()) // 2
                    y = (canvas_rect.height() - scaled_size.height()) // 2

                    # Apply opacity
                    old_opacity = painter.opacity()
                    painter.setOpacity(self.scene.background_opacity)

                    # Draw scaled background
                    painter.drawPixmap(x, y, scaled_size.width(), scaled_size.height(), pixmap)

                    # Restore opacity
                    painter.setOpacity(old_opacity)

            elif background_type.lower() in ["video", "mp4", "avi", "mov", "mkv", "webm"]:
                # For videos, we would need to extract a frame at the specified time
                # This is a simplified placeholder - in a full implementation, you would:
                # 1. Use a video processing library to extract the frame
                # 2. Cache extracted frames for performance
                # 3. Handle video time synchronization

                # Draw placeholder for video background
                painter.setPen(QPen(QColor("#007bff"), 2, Qt.PenStyle.DashLine))
                painter.setBrush(QBrush())
                canvas_rect = self.rect()

                # Draw video placeholder rectangle
                video_rect = QRect(
                    canvas_rect.x() + 20,
                    canvas_rect.y() + 20,
                    canvas_rect.width() - 40,
                    canvas_rect.height() - 40
                )
                painter.drawRect(video_rect)

                # Draw video info text
                painter.setPen(QPen(QColor("#007bff")))
                painter.setFont(QFont("", 12))
                info_text = f"🎬 Video Background\n{background_path}\nTime: {self.scene.background_video_time:.2f}s"
                painter.drawText(video_rect, Qt.AlignmentFlag.AlignCenter, info_text)

        except Exception as e:
            # Draw error indicator
            painter.setPen(QPen(QColor("#dc3545")))
            painter.setFont(QFont("", 10))
            painter.drawText(10, 30, f"Background error: {str(e)[:50]}...")

    def _draw_grid(self, painter: QPainter):
        """Draw grid lines"""
        painter.setPen(QPen(QColor("#e9ecef"), 1, Qt.PenStyle.DotLine))

        # Vertical lines
        x = self.grid_size
        while x < self.width():
            painter.drawLine(x, 0, x, self.height())
            x += self.grid_size

        # Horizontal lines
        y = self.grid_size
        while y < self.height():
            painter.drawLine(0, y, self.width(), y)
            y += self.grid_size

    def _draw_scene(self, painter: QPainter):
        """Draw the current scene"""
        if not self.scene:
            return

        # Get current scene state
        scene_at_time = self.scene.get_scene_at_time(self.scene.current_time)

        # Draw all visible tags
        for tag in scene_at_time.visual_tags.values():
            if tag.visible:
                self._draw_visual_tag(painter, tag)

        # Draw selection indicators
        if self.selected_tag_id and self.selected_tag_id in scene_at_time.visual_tags:
            selected_tag = scene_at_time.visual_tags[self.selected_tag_id]
            self._draw_selection(painter, selected_tag)

    def _draw_visual_tag(self, painter: QPainter, tag: VisualTag):
        """Draw a visual tag on the canvas"""
        # Convert 3D position to 2D canvas coordinates
        canvas_x = int(tag.transform.position.x)
        canvas_y = int(tag.transform.position.y)

        # Ensure tag is visible on canvas
        if (canvas_x < -self.tag_size or canvas_x > self.width() + self.tag_size or
            canvas_y < -self.tag_size or canvas_y > self.height() + self.tag_size):
            return

        # Get tag color based on type
        color = self._get_tag_color(tag.element_type)

        # Draw tag shape
        tag_rect = QRect(canvas_x - self.tag_size//2, canvas_y - self.tag_size//2,
                        self.tag_size, self.tag_size)

        # Background circle/shape
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor("#333333"), 2))
        painter.drawEllipse(tag_rect)

        # Draw type icon
        icon = self._get_tag_icon(tag.element_type)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("", 20))

        # Center the icon
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(icon)
        text_height = font_metrics.height()

        text_x = canvas_x - text_width // 2
        text_y = canvas_y + text_height // 4  # Slight offset for better centering

        painter.drawText(text_x, text_y, icon)

        # Draw name label if tag has a name
        if tag.name:
            painter.setPen(QPen(QColor("#333333")))
            painter.setFont(QFont("", 10))

            name_metrics = painter.fontMetrics()
            name_width = name_metrics.horizontalAdvance(tag.name)
            name_x = canvas_x - name_width // 2
            name_y = canvas_y + self.tag_size // 2 + 15

            # Draw background for text
            text_rect = QRect(name_x - 4, name_y - 12, name_width + 8, 16)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(QColor("#cccccc"), 1))
            painter.drawRoundedRect(text_rect, 3, 3)

            # Draw text
            painter.setPen(QPen(QColor("#333333")))
            painter.drawText(name_x, name_y, tag.name)

    def _draw_selection(self, painter: QPainter, tag: VisualTag):
        """Draw selection indicator around a tag"""
        canvas_x = int(tag.transform.position.x)
        canvas_y = int(tag.transform.position.y)

        selection_rect = QRect(canvas_x - self.tag_size//2 - self.selection_width,
                              canvas_y - self.tag_size//2 - self.selection_width,
                              self.tag_size + 2 * self.selection_width,
                              self.tag_size + 2 * self.selection_width)

        painter.setBrush(QBrush())  # No fill
        painter.setPen(QPen(QColor("#007bff"), self.selection_width, Qt.PenStyle.DashLine))
        painter.drawEllipse(selection_rect)

    def _draw_empty_state(self, painter: QPainter):
        """Draw empty state message"""
        painter.setPen(QPen(QColor("#6c757d")))
        painter.setFont(QFont("", 16))

        text = "Visual Canvas\n\nDrag objects here or use the toolbar\nto add visual elements to your scene"
        text_rect = self.rect()
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _get_tag_color(self, element_type: ElementType) -> QColor:
        """Get color for tag based on element type"""
        color_map = {
            ElementType.OBJECT: QColor("#28a745"),      # Green
            ElementType.CHARACTER: QColor("#007bff"),   # Blue
            ElementType.ENVIRONMENT: QColor("#6f42c1"), # Purple
            ElementType.LIGHT: QColor("#ffc107"),       # Yellow
            ElementType.CAMERA: QColor("#dc3545"),      # Red
            ElementType.EFFECT: QColor("#17a2b8")       # Cyan
        }
        return color_map.get(element_type, QColor("#6c757d"))  # Default gray

    def _get_tag_icon(self, element_type: ElementType) -> str:
        """Get icon character for tag based on element type"""
        icon_map = {
            ElementType.OBJECT: "📦",
            ElementType.CHARACTER: "👤",
            ElementType.ENVIRONMENT: "🏞️",
            ElementType.LIGHT: "💡",
            ElementType.CAMERA: "📷",
            ElementType.EFFECT: "✨"
        }
        return icon_map.get(element_type, "❓")

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on a tag
            clicked_tag = self._get_tag_at_position(event.position().toPoint())

            if clicked_tag:
                self.selected_tag_id = clicked_tag.id
                self.dragging_tag = clicked_tag.id
                self.last_mouse_pos = event.position().toPoint()
                self.tag_selected.emit(clicked_tag.id)
                self.log.debug(f"Selected tag: {clicked_tag.name}")
            else:
                # Click on empty area - clear selection
                self.selected_tag_id = None
                self.dragging_tag = None
                self.tag_selected.emit("")

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events"""
        if self.dragging_tag and self.scene:
            # Calculate movement delta
            delta = event.position().toPoint() - self.last_mouse_pos

            # Update tag position
            tag = self.scene.visual_tags.get(self.dragging_tag)
            if tag:
                new_x = tag.transform.position.x + delta.x()
                new_y = tag.transform.position.y + delta.y()

                # Update via composer service to trigger spatial relationship updates
                if self.composer_service:
                    self.composer_service.update_tag_position(self.dragging_tag, new_x, new_y)
                else:
                    # Fallback to direct update
                    tag.transform.position.x = new_x
                    tag.transform.position.y = new_y

                self.tag_moved.emit(self.dragging_tag, new_x, new_y)
                self.update()

            self.last_mouse_pos = event.position().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_tag = None

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click events"""
        clicked_tag = self._get_tag_at_position(event.position().toPoint())
        if clicked_tag:
            self.tag_double_clicked.emit(clicked_tag.id)
            self.log.debug(f"Double-clicked tag: {clicked_tag.name}")

    def _get_tag_at_position(self, pos: QPoint) -> VisualTag:
        """Get the tag at the given position"""
        if not self.scene:
            return None

        # Check all tags in reverse order (top to bottom)
        scene_at_time = self.scene.get_scene_at_time(self.scene.current_time)
        tags_by_depth = scene_at_time.get_tags_by_depth_order()

        for tag in reversed(tags_by_depth):  # Check front-most tags first
            if not tag.visible:
                continue

            canvas_x = int(tag.transform.position.x)
            canvas_y = int(tag.transform.position.y)

            # Check if position is within tag bounds
            tag_rect = QRect(canvas_x - self.tag_size//2, canvas_y - self.tag_size//2,
                           self.tag_size, self.tag_size)

            if tag_rect.contains(pos):
                return tag

        return None

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        # TODO: Implement canvas zooming
        # delta = event.angleDelta().y()
        # zoom_factor = 1.1 if delta > 0 else 0.9
        # self.canvas_scale *= zoom_factor
        # self.update()
        pass