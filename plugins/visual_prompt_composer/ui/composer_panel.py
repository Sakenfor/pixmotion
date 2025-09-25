"""
Visual Prompt Composer Panel

Main UI panel for the visual prompt composer plugin.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolBar,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QStatusBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction

from framework.modern_ui import apply_modern_style, ModernSplitter
from .canvas_widget import CanvasWidget
from .timeline_widget import TimelineWidget
from .properties_panel import PropertiesPanel


class VisualPromptComposerPanel(QWidget):
    """Main panel for visual prompt composition"""

    # Signals
    scene_changed = pyqtSignal(str)  # scene_id
    tag_selected = pyqtSignal(str)   # tag_id

    def __init__(self, framework):
        super().__init__()
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.composer_service = None
        self.theme_manager = framework.get_service("theme_manager")

        self._init_ui()
        self._connect_signals()
        self._apply_modern_styling()

        # Initialize after UI is set up
        self._init_services()

    def _init_services(self):
        """Initialize composer service reference"""
        try:
            self.composer_service = self.framework.get_service("visual_composer_service")
            if self.composer_service:
                # Check if service is properly initialized
                if hasattr(self.composer_service, 'log') and self.composer_service.log:
                    self.log.debug("Connected to visual composer service")
                    # Create a default scene
                    self.composer_service.new_scene("Demo Scene")
                    self._update_scene_info()
                else:
                    self.log.warning("Composer service not fully initialized yet, will retry later")
                    # Schedule a retry
                    self.framework.get_service("worker_manager").schedule_task(self._retry_service_init, delay=1.0)
        except Exception as e:
            self.log.error(f"Failed to initialize composer services: {e}")

    def _retry_service_init(self):
        """Retry service initialization after delay"""
        try:
            if self.composer_service and hasattr(self.composer_service, 'log'):
                self.log.debug("Retrying composer service initialization")
                self.composer_service.new_scene("Demo Scene")
                self._update_scene_info()
        except Exception as e:
            self.log.error(f"Failed to retry composer service initialization: {e}")

    def _init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Create toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Create main content area with vertical splitter
        main_splitter = ModernSplitter(Qt.Orientation.Vertical)

        # Top section - Canvas and Properties (horizontal splitter)
        top_splitter = ModernSplitter(Qt.Orientation.Horizontal)

        # Left panel - Canvas
        canvas_frame = QFrame()
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(4, 4, 4, 4)

        # Canvas header
        canvas_header = QLabel("🎨 Visual Canvas")
        canvas_header.setFont(QFont("", 14, QFont.Weight.Bold))
        canvas_layout.addWidget(canvas_header)

        # Canvas widget
        self.canvas = CanvasWidget(self.framework)
        canvas_layout.addWidget(self.canvas, 1)

        top_splitter.addWidget(canvas_frame)

        # Right panel - Properties
        self.properties_panel = PropertiesPanel(self.framework)
        top_splitter.addWidget(self.properties_panel)

        # Set horizontal splitter proportions (70% canvas, 30% properties)
        top_splitter.setSizes([700, 300])

        main_splitter.addWidget(top_splitter)

        # Bottom section - Timeline
        timeline_frame = QFrame()
        timeline_layout = QVBoxLayout(timeline_frame)
        timeline_layout.setContentsMargins(4, 4, 4, 4)

        # Timeline header
        timeline_header = QLabel("🎬 Animation Timeline")
        timeline_header.setFont(QFont("", 12, QFont.Weight.Bold))
        timeline_layout.addWidget(timeline_header)

        # Timeline widget
        self.timeline = TimelineWidget(self.framework)
        timeline_layout.addWidget(self.timeline, 1)

        main_splitter.addWidget(timeline_frame)

        # Set vertical splitter proportions (75% top, 25% timeline)
        main_splitter.setSizes([600, 200])

        main_layout.addWidget(main_splitter, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.scene_info_label = QLabel("No scene loaded")
        self.status_bar.addPermanentWidget(self.scene_info_label)
        main_layout.addWidget(self.status_bar)

    def _create_toolbar(self) -> QToolBar:
        """Create the main toolbar"""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # Scene operations
        new_action = QAction("🆕 New Scene", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_scene)
        toolbar.addAction(new_action)

        save_action = QAction("💾 Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_scene)
        toolbar.addAction(save_action)

        load_action = QAction("📁 Load", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self._load_scene)
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        # Tag operations
        add_object_action = QAction("📦 Add Object", self)
        add_object_action.triggered.connect(self._add_object_tag)
        toolbar.addAction(add_object_action)

        add_character_action = QAction("👤 Add Character", self)
        add_character_action.triggered.connect(self._add_character_tag)
        toolbar.addAction(add_character_action)

        toolbar.addSeparator()

        # Background operations
        background_action = QAction("🖼️ Set Background", self)
        background_action.setToolTip("Set scene background from assets")
        background_action.triggered.connect(self._set_background)
        toolbar.addAction(background_action)

        clear_bg_action = QAction("🚫 Clear Background", self)
        clear_bg_action.setToolTip("Clear scene background")
        clear_bg_action.triggered.connect(self._clear_background)
        toolbar.addAction(clear_bg_action)

        toolbar.addSeparator()

        # Generation operations
        generate_action = QAction("✨ Generate Prompt", self)
        generate_action.setShortcut("F5")
        generate_action.triggered.connect(self._generate_prompt)
        toolbar.addAction(generate_action)

        export_action = QAction("🚀 Export to Generator", self)
        export_action.triggered.connect(self._export_to_generator)
        toolbar.addAction(export_action)

        return toolbar

    def _connect_signals(self):
        """Connect internal signals"""
        # Canvas signals
        self.canvas.tag_selected.connect(self._on_tag_selected)
        self.canvas.tag_moved.connect(self._on_tag_moved)
        self.canvas.tag_double_clicked.connect(self._on_tag_double_clicked)

        # Timeline signals
        self.timeline.time_changed.connect(self._on_timeline_changed)
        self.timeline.keyframe_modified.connect(self._on_keyframe_modified)
        self.timeline.playback_toggled.connect(self._on_playback_toggled)

        # Properties panel signals
        self.properties_panel.tag_updated.connect(self._on_tag_updated)
        self.properties_panel.keyframe_set.connect(self._on_keyframe_set)

    def _apply_modern_styling(self):
        """Apply modern styling to the panel"""
        if self.theme_manager:
            apply_modern_style(self, self.theme_manager, "card")

    # Scene operations
    def _new_scene(self):
        """Create a new scene"""
        try:
            if not self.composer_service:
                QMessageBox.warning(self, "Error", "Composer service not available")
                return

            # TODO: Add scene name dialog
            scene = self.composer_service.new_scene("New Scene")
            if scene:
                self._update_scene_info()
                self.canvas.set_scene(scene)
                self.timeline.set_scene(scene)
                self.properties_panel.set_scene(scene)
                self.log.info("Created new scene")
        except Exception as e:
            self.log.error(f"Failed to create new scene: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create new scene: {e}")

    def _save_scene(self):
        """Save the current scene"""
        try:
            if not self.composer_service or not self.composer_service.get_current_scene():
                QMessageBox.warning(self, "Error", "No scene to save")
                return

            # Get save location
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Save Scene",
                f"{self.composer_service.get_current_scene().name}.json",
                "JSON Files (*.json);;All Files (*)"
            )

            if filepath:
                success = self.composer_service.save_scene(filepath=filepath)
                if success:
                    QMessageBox.information(self, "Success", f"Scene saved to {filepath}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to save scene")

        except Exception as e:
            self.log.error(f"Failed to save scene: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save scene: {e}")

    def _load_scene(self):
        """Load a scene from file"""
        try:
            if not self.composer_service:
                QMessageBox.warning(self, "Error", "Composer service not available")
                return

            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Load Scene",
                "",
                "JSON Files (*.json);;All Files (*)"
            )

            if filepath:
                scene = self.composer_service.load_scene(filepath)
                if scene:
                    self._update_scene_info()
                    self.canvas.set_scene(scene)
                    self.timeline.set_scene(scene)
                    self.properties_panel.set_scene(scene)
                    QMessageBox.information(self, "Success", f"Scene loaded from {filepath}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to load scene")

        except Exception as e:
            self.log.error(f"Failed to load scene: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load scene: {e}")

    # Tag operations
    def _add_object_tag(self):
        """Add an object tag to the scene"""
        try:
            if not self.composer_service:
                return

            from ..models.visual_tag import ElementType
            tag = self.composer_service.create_basic_tag(
                name=f"Object_{len(self.composer_service.get_current_scene().visual_tags) + 1}",
                element_type=ElementType.OBJECT,
                position=(100, 100, 0)
            )

            success = self.composer_service.add_visual_tag(tag)
            if success:
                self.canvas.refresh()
                self.log.debug(f"Added object tag: {tag.name}")

        except Exception as e:
            self.log.error(f"Failed to add object tag: {e}")

    def _add_character_tag(self):
        """Add a character tag to the scene"""
        try:
            if not self.composer_service:
                return

            from ..models.visual_tag import ElementType
            tag = self.composer_service.create_basic_tag(
                name=f"Character_{len(self.composer_service.get_current_scene().visual_tags) + 1}",
                element_type=ElementType.CHARACTER,
                position=(200, 200, 0)
            )

            success = self.composer_service.add_visual_tag(tag)
            if success:
                self.canvas.refresh()
                self.log.debug(f"Added character tag: {tag.name}")

        except Exception as e:
            self.log.error(f"Failed to add character tag: {e}")

    # Generation operations
    def _generate_prompt(self):
        """Generate prompt for current scene"""
        try:
            if not self.composer_service:
                QMessageBox.warning(self, "Error", "Composer service not available")
                return

            prompt = self.composer_service.generate_prompt()
            if prompt:
                # Show prompt in a dialog
                QMessageBox.information(self, "Generated Prompt", f"Generated prompt:\n\n{prompt}")
            else:
                QMessageBox.warning(self, "Warning", "No prompt generated")

        except Exception as e:
            self.log.error(f"Failed to generate prompt: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate prompt: {e}")

    def _export_to_generator(self):
        """Export generated prompt to the video generator"""
        try:
            if not self.composer_service:
                QMessageBox.warning(self, "Error", "Composer service not available")
                return

            success = self.composer_service.export_to_generator()
            if success:
                QMessageBox.information(self, "Success", "Prompt exported to generator")
            else:
                QMessageBox.warning(self, "Warning", "Failed to export prompt")

        except Exception as e:
            self.log.error(f"Failed to export to generator: {e}")
            QMessageBox.critical(self, "Error", f"Failed to export to generator: {e}")

    def _update_scene_info(self):
        """Update scene information display"""
        if self.composer_service and self.composer_service.get_current_scene():
            scene = self.composer_service.get_current_scene()
            stats = self.composer_service.get_scene_statistics()
            info_text = f"Scene: {scene.name} | Tags: {stats.get('tag_count', 0)} | Duration: {scene.duration}s"
            self.scene_info_label.setText(info_text)
        else:
            self.scene_info_label.setText("No scene loaded")

    def refresh_ui(self):
        """Refresh the UI to reflect current state"""
        self._update_scene_info()
        if hasattr(self, 'canvas'):
            self.canvas.refresh()
        if hasattr(self, 'timeline'):
            self.timeline.refresh_tracks()

    # Signal handlers for inter-panel communication

    def _on_tag_selected(self, tag_id: str):
        """Handle tag selection from canvas"""
        if not self.composer_service or not self.composer_service.get_current_scene():
            return

        scene = self.composer_service.get_current_scene()
        selected_tag = scene.get_visual_tag(tag_id) if tag_id else None

        # Update properties panel
        self.properties_panel.set_selected_tag(selected_tag)

        if selected_tag:
            self.log.debug(f"Selected tag: {selected_tag.name or selected_tag.id[:8]}")

    def _on_tag_moved(self, tag_id: str, x: float, y: float):
        """Handle tag movement from canvas"""
        # The canvas already updates via the composer service
        # Just refresh properties panel if this tag is selected
        if (hasattr(self.properties_panel, 'selected_tag') and
            self.properties_panel.selected_tag and
            self.properties_panel.selected_tag.id == tag_id):
            self.properties_panel._update_ui_from_tag()

    def _on_tag_double_clicked(self, tag_id: str):
        """Handle tag double-click from canvas"""
        # Focus on properties panel for this tag
        if not self.composer_service or not self.composer_service.get_current_scene():
            return

        scene = self.composer_service.get_current_scene()
        tag = scene.get_visual_tag(tag_id)
        if tag:
            self.properties_panel.set_selected_tag(tag)
            self.log.debug(f"Double-clicked tag: {tag.name or tag.id[:8]}")

    def _on_timeline_changed(self, current_time: float):
        """Handle timeline position change"""
        # Update properties panel current time
        self.properties_panel.set_current_time(current_time)

        # Update scene current time
        if self.composer_service and self.composer_service.get_current_scene():
            scene = self.composer_service.get_current_scene()
            scene.current_time = current_time

            # Refresh canvas to show scene at this time
            self.canvas.refresh()

    def _on_keyframe_modified(self, tag_id: str, property_name: str, time: float, value):
        """Handle keyframe modification from timeline"""
        if not self.composer_service or not self.composer_service.get_current_scene():
            return

        scene = self.composer_service.get_current_scene()
        tag = scene.get_visual_tag(tag_id)

        if not tag:
            return

        try:
            if value is None:
                # Remove keyframe
                tag.remove_keyframe(property_name, time)
                self.log.debug(f"Removed keyframe: {tag.name}.{property_name} at {time}s")
            else:
                # Add/update keyframe
                tag.set_keyframe(property_name, time, value)
                self.log.debug(f"Set keyframe: {tag.name}.{property_name} = {value} at {time}s")

            # Refresh timeline to show changes
            self.timeline.refresh_tracks()

        except Exception as e:
            self.log.error(f"Failed to modify keyframe: {e}")

    def _on_playback_toggled(self, is_playing: bool):
        """Handle timeline playback toggle"""
        if is_playing:
            self.log.debug("Timeline playback started")
        else:
            self.log.debug("Timeline playback stopped")

    def _on_tag_updated(self, tag_id: str, updates: dict):
        """Handle tag property updates from properties panel"""
        if not self.composer_service:
            return

        # Update via composer service to trigger spatial analysis
        success = self.composer_service.update_visual_tag(tag_id, updates)

        if success:
            # Refresh canvas to show changes
            self.canvas.refresh()
            # Update scene info
            self._update_scene_info()

    def _on_keyframe_set(self, tag_id: str, property_name: str, time: float, value):
        """Handle keyframe setting from properties panel"""
        if not self.composer_service or not self.composer_service.get_current_scene():
            return

        scene = self.composer_service.get_current_scene()
        tag = scene.get_visual_tag(tag_id)

        if tag:
            try:
                tag.set_keyframe(property_name, time, value)
                self.log.debug(f"Set keyframe from properties: {tag.name}.{property_name} = {value} at {time}s")

                # Refresh timeline to show new keyframe
                self.timeline.refresh_tracks()

            except Exception as e:
                self.log.error(f"Failed to set keyframe: {e}")

    # Background operations

    def _set_background(self):
        """Open asset browser to set scene background"""
        try:
            if not self.composer_service or not self.composer_service.get_current_scene():
                QMessageBox.warning(self, "Error", "No scene available")
                return

            from .asset_browser_dialog import AssetBrowserDialog
            dialog = AssetBrowserDialog(self.framework, self)

            # Set current background if any
            scene = self.composer_service.get_current_scene()
            if scene.background_asset_id:
                dialog.set_current_background(
                    scene.background_asset_id,
                    scene.background_type or "",
                    scene.background_video_time,
                    scene.background_opacity,
                    scene.background_scale
                )

            # Connect dialog signal
            dialog.asset_selected.connect(self._on_background_selected)
            dialog.exec()

        except Exception as e:
            self.log.error(f"Failed to open background selector: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open background selector: {e}")

    def _clear_background(self):
        """Clear scene background"""
        try:
            if not self.composer_service or not self.composer_service.get_current_scene():
                return

            scene = self.composer_service.get_current_scene()
            scene.background_asset_id = None
            scene.background_type = None
            scene.background_video_time = 0.0
            scene.background_opacity = 1.0
            scene.background_scale = 1.0

            # Refresh canvas
            self.canvas.refresh()
            self.log.info("Cleared scene background")

        except Exception as e:
            self.log.error(f"Failed to clear background: {e}")

    def _on_background_selected(self, asset_id: str, asset_type: str, video_time: float, opacity: float, scale: float):
        """Handle background asset selection"""
        try:
            if not self.composer_service or not self.composer_service.get_current_scene():
                return

            scene = self.composer_service.get_current_scene()

            if asset_id:  # Asset selected
                scene.background_asset_id = asset_id
                scene.background_type = asset_type
                scene.background_video_time = video_time
                scene.background_opacity = opacity
                scene.background_scale = scale
                self.log.info(f"Set background to asset {asset_id} ({asset_type})")
            else:  # Clear background
                scene.background_asset_id = None
                scene.background_type = None
                scene.background_video_time = 0.0
                scene.background_opacity = 1.0
                scene.background_scale = 1.0
                self.log.info("Cleared scene background")

            # Refresh canvas to show changes
            self.canvas.refresh()

        except Exception as e:
            self.log.error(f"Failed to set background: {e}")