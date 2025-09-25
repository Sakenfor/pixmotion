"""
Asset Browser Dialog

Dialog for selecting images or videos from the asset library as scene backgrounds.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QSlider, QSpinBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QFont

from framework.modern_ui import apply_modern_style


class AssetPreviewWidget(QLabel):
    """Widget for displaying asset preview"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setMaximumSize(400, 300)
        self.setStyleSheet("""
            AssetPreviewWidget {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("No asset selected\n\nSelect an image or video\nfrom the list to preview")

    def set_asset_preview(self, asset_path: str, asset_type: str):
        """Set preview for an asset"""
        try:
            if asset_type in ["image", "jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                pixmap = QPixmap(asset_path)
                if not pixmap.isNull():
                    # Scale pixmap to fit widget
                    scaled_pixmap = pixmap.scaled(
                        self.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.setPixmap(scaled_pixmap)
                else:
                    self.setText(f"Cannot load image:\n{asset_path}")
            elif asset_type in ["video", "mp4", "avi", "mov", "mkv", "webm"]:
                # For videos, show a placeholder with video info
                self.setText(f"🎬 Video Preview\n\n{asset_path}\n\nVideo backgrounds will show\na specific frame that you can\nchoose with the time slider")
            else:
                self.setText(f"Unsupported asset type:\n{asset_type}")

        except Exception as e:
            self.setText(f"Error loading preview:\n{str(e)}")


class AssetBrowserDialog(QDialog):
    """Dialog for browsing and selecting assets as scene backgrounds"""

    asset_selected = pyqtSignal(str, str, float, float, float)  # asset_id, asset_type, video_time, opacity, scale

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.asset_service = framework.get_service("asset_service")
        self.theme_manager = framework.get_service("theme_manager")

        self.selected_asset = None
        self.selected_asset_type = None

        self._init_ui()
        self._load_assets()
        self._apply_modern_styling()

    def _init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Select Background Asset")
        self.setModal(True)
        self.resize(800, 600)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Header
        header = QLabel("🖼️ Choose Background Asset")
        header.setFont(QFont("", 16, QFont.Weight.Bold))
        main_layout.addWidget(header)

        # Content area
        content_layout = QHBoxLayout()

        # Left side - Asset list
        left_group = QGroupBox("Available Assets")
        left_group.setMinimumWidth(350)
        left_layout = QVBoxLayout(left_group)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Type:"))

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Images", "Videos"])
        self.type_filter.currentTextChanged.connect(self._filter_assets)
        filter_layout.addWidget(self.type_filter)
        filter_layout.addStretch()

        left_layout.addLayout(filter_layout)

        # Asset list
        self.asset_list = QListWidget()
        self.asset_list.setMinimumWidth(320)
        self.asset_list.setMinimumHeight(300)
        self.asset_list.itemClicked.connect(self._on_asset_selected)
        left_layout.addWidget(self.asset_list)

        content_layout.addWidget(left_group)

        # Right side - Preview and settings
        right_group = QGroupBox("Preview & Settings")
        right_group.setMinimumWidth(400)
        right_layout = QVBoxLayout(right_group)

        # Preview
        self.preview_widget = AssetPreviewWidget()
        right_layout.addWidget(self.preview_widget)

        # Settings
        settings_group = QGroupBox("Background Settings")
        settings_layout = QFormLayout(settings_group)

        # Video time slider (for video assets)
        video_time_layout = QHBoxLayout()
        self.video_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.video_time_slider.setRange(0, 1000)  # 0-100% of video duration
        self.video_time_slider.setValue(0)
        self.video_time_spin = QDoubleSpinBox()
        self.video_time_spin.setRange(0.0, 100.0)
        self.video_time_spin.setSuffix("s")
        self.video_time_spin.setDecimals(2)

        video_time_layout.addWidget(self.video_time_slider)
        video_time_layout.addWidget(self.video_time_spin)

        settings_layout.addRow("Video Time:", video_time_layout)

        # Opacity slider
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setSuffix("%")

        # Connect opacity controls
        self.opacity_slider.valueChanged.connect(self.opacity_spin.setValue)
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)

        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_spin)

        settings_layout.addRow("Opacity:", opacity_layout)

        # Scale slider
        scale_layout = QHBoxLayout()
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 300)  # 10% to 300%
        self.scale_slider.setValue(100)
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(10, 300)
        self.scale_spin.setValue(100)
        self.scale_spin.setSuffix("%")

        # Connect scale controls
        self.scale_slider.valueChanged.connect(self.scale_spin.setValue)
        self.scale_spin.valueChanged.connect(self.scale_slider.setValue)

        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_spin)

        settings_layout.addRow("Scale:", scale_layout)

        right_layout.addWidget(settings_group)
        right_layout.addStretch()

        content_layout.addWidget(right_group, 1)
        main_layout.addLayout(content_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.clear_button = QPushButton("Clear Background")
        self.clear_button.clicked.connect(self._clear_background)
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        self.select_button = QPushButton("Select Asset")
        self.select_button.setEnabled(False)
        self.select_button.clicked.connect(self._select_asset)
        button_layout.addWidget(self.select_button)

        main_layout.addLayout(button_layout)

        # Initially hide video controls
        self._update_video_controls_visibility()

    def _apply_modern_styling(self):
        """Apply modern styling to the dialog"""
        if self.theme_manager:
            apply_modern_style(self, self.theme_manager, "dialog")

    def _load_assets(self):
        """Load assets from the asset service"""
        if not self.asset_service:
            return

        try:
            assets = []

            # Try to get assets through the asset service
            if self.asset_service:
                try:
                    if hasattr(self.asset_service, 'get_all_assets'):
                        assets = self.asset_service.get_all_assets()
                    elif hasattr(self.asset_service, 'assets'):
                        assets = self.asset_service.assets
                    elif hasattr(self.asset_service, 'get_assets'):
                        assets = self.asset_service.get_assets()
                except Exception as e:
                    self.framework.get_service("log_manager").debug(f"Asset service error: {e}")

            # If no assets from service, add some demo/example entries
            if not assets:
                assets = [
                    {"id": "browse_files", "name": "🗂️ Browse Files...", "type": "browse", "path": ""},
                    {"id": "demo_image_1", "name": "📁 Select from filesystem", "type": "filesystem", "path": ""},
                    {"id": "placeholder_1", "name": "💡 Import assets first", "type": "info", "path": ""},
                ]

            for asset in assets:
                self._add_asset_to_list(asset)

            # Add helpful message if no real assets
            if len(assets) <= 3:
                help_item = QListWidgetItem("ℹ️ To add assets:")
                help_item.setData(Qt.ItemDataRole.UserRole, None)
                self.asset_list.addItem(help_item)

                help_item2 = QListWidgetItem("  1. Use Asset Browser to scan folders")
                help_item2.setData(Qt.ItemDataRole.UserRole, None)
                self.asset_list.addItem(help_item2)

                help_item3 = QListWidgetItem("  2. Or browse files directly")
                help_item3.setData(Qt.ItemDataRole.UserRole, None)
                self.asset_list.addItem(help_item3)

        except Exception as e:
            # Add error message
            error_item = QListWidgetItem(f"Error loading assets: {str(e)}")
            error_item.setData(Qt.ItemDataRole.UserRole, None)
            self.asset_list.addItem(error_item)

    def _add_asset_to_list(self, asset):
        """Add an asset to the list widget"""
        try:
            asset_name = asset.get("name", "Unknown Asset")
            asset_type = asset.get("type", "unknown")
            asset_path = asset.get("path", "")

            # Create list item
            item_text = f"{asset_name} ({asset_type.upper()})"
            item = QListWidgetItem(item_text)

            # Store asset data
            item.setData(Qt.ItemDataRole.UserRole, asset)

            # Set icon based on type
            if asset_type in ["image", "jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                item.setIcon(QIcon("🖼️"))  # Image icon
            elif asset_type in ["video", "mp4", "avi", "mov", "mkv", "webm"]:
                item.setIcon(QIcon("🎬"))  # Video icon
            else:
                item.setIcon(QIcon("📄"))  # Generic file icon

            self.asset_list.addItem(item)

        except Exception as e:
            # Create error item
            error_item = QListWidgetItem(f"Error loading asset: {str(e)}")
            error_item.setData(Qt.ItemDataRole.UserRole, None)
            self.asset_list.addItem(error_item)

    def _filter_assets(self, filter_type: str):
        """Filter assets by type"""
        for i in range(self.asset_list.count()):
            item = self.asset_list.item(i)
            asset = item.data(Qt.ItemDataRole.UserRole)

            if not asset:
                continue

            asset_type = asset.get("type", "").lower()

            if filter_type == "All":
                item.setHidden(False)
            elif filter_type == "Images":
                item.setHidden(asset_type not in ["image", "jpg", "jpeg", "png", "gif", "bmp", "webp"])
            elif filter_type == "Videos":
                item.setHidden(asset_type not in ["video", "mp4", "avi", "mov", "mkv", "webm"])

    def _on_asset_selected(self, item: QListWidgetItem):
        """Handle asset selection"""
        asset = item.data(Qt.ItemDataRole.UserRole)

        if not asset:
            self.selected_asset = None
            self.selected_asset_type = None
            self.select_button.setEnabled(False)
            self.preview_widget.setText("Invalid asset selected")
            return

        self.selected_asset = asset
        self.selected_asset_type = asset.get("type", "unknown")
        self.select_button.setEnabled(True)

        # Update preview
        asset_path = asset.get("path", "")
        self.preview_widget.set_asset_preview(asset_path, self.selected_asset_type)

        # Update video controls visibility
        self._update_video_controls_visibility()

    def _update_video_controls_visibility(self):
        """Show/hide video controls based on selected asset type"""
        is_video = (self.selected_asset_type and
                   self.selected_asset_type.lower() in ["video", "mp4", "avi", "mov", "mkv", "webm"])

        # Enable/disable video time controls
        self.video_time_slider.setEnabled(is_video)
        self.video_time_spin.setEnabled(is_video)

    def _clear_background(self):
        """Clear the background (select no asset)"""
        self.asset_selected.emit("", "", 0.0, 1.0, 1.0)  # Empty asset
        self.accept()

    def _select_asset(self):
        """Select the current asset"""
        if not self.selected_asset:
            return

        asset_id = self.selected_asset.get("id", "")
        asset_type = self.selected_asset_type or ""
        video_time = self.video_time_spin.value()
        opacity = self.opacity_spin.value() / 100.0
        scale = self.scale_spin.value() / 100.0

        self.asset_selected.emit(asset_id, asset_type, video_time, opacity, scale)
        self.accept()

    def set_current_background(self, asset_id: str, asset_type: str, video_time: float, opacity: float, scale: float):
        """Set the current background settings"""
        # Find and select the asset in the list
        for i in range(self.asset_list.count()):
            item = self.asset_list.item(i)
            asset = item.data(Qt.ItemDataRole.UserRole)
            if asset and asset.get("id") == asset_id:
                self.asset_list.setCurrentItem(item)
                self._on_asset_selected(item)
                break

        # Set control values
        self.video_time_spin.setValue(video_time)
        self.opacity_spin.setValue(int(opacity * 100))
        self.scale_spin.setValue(int(scale * 100))