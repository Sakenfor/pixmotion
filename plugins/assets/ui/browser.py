# D:/My Drive/code/pixmotion/plugins/assets/ui/browser.py
import os
import uuid
import json
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeView,
    QToolButton,
    QListView,
    QFileDialog,
    QSplitter,
    QMenu,
    QStyle,
    QHBoxLayout,
    QLabel,
    QButtonGroup,
    QWidgetAction,
    QMessageBox,
    QStackedWidget,
    QPushButton,
)
from PyQt6.QtCore import Qt, QSize, QModelIndex, pyqtSignal
from PyQt6.QtGui import QIcon, QStandardItemModel, QStandardItem, QPixmap

from plugins.core.models import Asset
from .views import AssetModel, AssetDelegate
from .widgets import AssetHoverManager, StarRatingFilter
from .windows import MediaPreviewWindow
from .dialogs import CreatePackageDialog
from .package_editor_widget import PackageEditorWidget  # MODIFIED: Import from its new local file
from .ai_settings_dialog import AIProviderSettingsDialog
from framework.manifests import EmotionPackageManifest
from framework.modern_ui import ModernCard, ModernSplitter, apply_modern_style


class AssetBrowserPanel(QWidget):
    """A panel for browsing the asset library with a custom title bar."""

    assets_loaded_signal = pyqtSignal(list)
    thumbnail_loaded_signal = pyqtSignal(str, QPixmap)

    def __init__(self, framework):
        super().__init__()
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.settings = framework.get_service("settings_service")
        self.events = framework.get_service("event_manager")
        self.db = framework.get_service("database_service")
        self.commands = framework.get_service("command_manager")
        self.asset_manager = framework.get_service("asset_manager")
        self.theme_manager = framework.get_service("theme_manager")

        self._current_folder_assets = []
        self._rating_filter = 0
        self._type_filter = "all"
        self._tag_filters = {}  # layer_id -> [selected_tags]

        self.thumbnail_queue = set()
        self.thumbnail_cache = {}
        self.folder_model = QStandardItemModel()
        self.asset_model = AssetModel(self.log)
        self.pinned_previews = []
        self.current_folder = None

        self._init_ui()
        self._connect_signals()
        self._apply_theme()
        self.refresh_folders()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Modern header with better styling
        self._header_bar = self._create_modern_header()
        layout.addWidget(self._header_bar)

        # Create filter widgets
        self._create_filter_widgets()

        splitter = ModernSplitter(Qt.Orientation.Horizontal)

        # Create modern left pane card
        left_pane = ModernCard("📁 Folders")
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(4)

        self.folder_tree = QTreeView()
        self.folder_tree.setModel(self.folder_model)
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.setIndentation(20)
        # Apply modern styling to folder tree
        apply_modern_style(self.folder_tree, self.theme_manager, "sidebar")
        left_layout.addWidget(self.folder_tree)

        self.right_pane_stack = QStackedWidget()

        self.asset_view = QListView()
        self.asset_view.setModel(self.asset_model)
        self.asset_view.setViewMode(QListView.ViewMode.IconMode)
        self.asset_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.asset_view.setSpacing(8)  # Increased spacing for modern look
        self.asset_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.asset_view.setMouseTracking(True)
        self.asset_view.setUniformItemSizes(True)
        self.asset_view.setDragEnabled(True)
        self.asset_delegate = AssetDelegate(self.asset_view)
        self.asset_view.setItemDelegate(self.asset_delegate)
        grid_size = self.asset_delegate.item_size()
        self.asset_view.setGridSize(grid_size)
        self.asset_view.setIconSize(QSize(self.asset_delegate.thumbnail_size, self.asset_delegate.thumbnail_size))
        self.hover_manager = AssetHoverManager(self.asset_view)
        self.asset_view.viewport().installEventFilter(self.hover_manager)

        # Apply modern styling to asset view
        apply_modern_style(self.asset_view, self.theme_manager, "modern_list")

        self.package_editor = PackageEditorWidget(self.framework)

        self.right_pane_stack.addWidget(self.asset_view)
        self.right_pane_stack.addWidget(self.package_editor)

        splitter.addWidget(left_pane)
        splitter.addWidget(self.right_pane_stack)
        splitter.setSizes([250, 550])
        layout.addWidget(self._header_bar)
        layout.addWidget(splitter, 1)

    def _create_modern_header(self):
        """Create a modern, themed header bar"""
        header_bar = QWidget()
        header_bar.setFixedHeight(52)  # Slightly taller for better proportions

        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(16, 8, 16, 8)  # More generous margins
        header_layout.setSpacing(12)  # Better spacing

        # Title section with better styling
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)

        icon_label = QLabel("🎨")
        icon_label.setStyleSheet("font-size: 20px; padding: 2px;")
        title_layout.addWidget(icon_label)

        title_label = QLabel("Asset Browser")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; margin: 0; padding: 0;")
        title_layout.addWidget(title_label)

        header_layout.addWidget(title_container)
        header_layout.addStretch()

        # Button groups with proper spacing
        self._create_button_toolbar(header_layout)

        return header_bar

    def _create_button_toolbar(self, layout):
        """Create the main button toolbar with proper grouping"""
        # Folder management buttons
        folder_frame = QWidget()
        folder_layout = QHBoxLayout(folder_frame)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(4)

        self.add_folder_btn = self._create_toolbar_button("📁", "Add Library Folder")
        self.clear_clipboard_btn = self._create_toolbar_button("🗑️", "Clear Clipboard")
        folder_layout.addWidget(self.add_folder_btn)
        folder_layout.addWidget(self.clear_clipboard_btn)

        layout.addWidget(folder_frame)
        layout.addWidget(self._create_separator())

        # AI tools buttons
        ai_frame = QWidget()
        ai_layout = QHBoxLayout(ai_frame)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.setSpacing(4)

        self.ai_tag_btn = self._create_toolbar_button("🤖", "AI Tagging")
        self.ai_filter_btn = self._create_toolbar_button("🏷️", "AI Filters")
        ai_layout.addWidget(self.ai_tag_btn)
        ai_layout.addWidget(self.ai_filter_btn)

        layout.addWidget(ai_frame)
        layout.addWidget(self._create_separator())

        # View tools buttons
        view_frame = QWidget()
        view_layout = QHBoxLayout(view_frame)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(4)

        self.filter_btn = self._create_toolbar_button("🔍", "Filter & Search")
        view_layout.addWidget(self.filter_btn)

        layout.addWidget(view_frame)

    def _create_toolbar_button(self, icon_text, tooltip):
        """Create a consistently styled toolbar button"""
        btn = QToolButton()
        btn.setText(icon_text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(36, 36)  # Consistent button size
        btn.setStyleSheet("""
            QToolButton {
                border: 1px solid transparent;
                border-radius: 8px;
                font-size: 16px;
                padding: 2px;
                margin: 0;
            }
        """)
        return btn

    def _create_separator(self):
        """Create a visual separator between button groups"""
        separator = QLabel("│")
        separator.setFixedWidth(16)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator.setStyleSheet("font-size: 14px; margin: 0 4px;")
        return separator

    def _apply_theme(self):
        """Apply the current theme to all UI components with modern styling"""
        if not self.theme_manager:
            return

        # Apply modern header styling
        if hasattr(self, '_header_bar'):
            apply_modern_style(self._header_bar, self.theme_manager, "header")

        # Apply modern sidebar styling to folder tree
        if hasattr(self, 'folder_tree'):
            apply_modern_style(self.folder_tree, self.theme_manager, "sidebar")

        # Apply modern list styling to asset view
        if hasattr(self, 'asset_view'):
            apply_modern_style(self.asset_view, self.theme_manager, "modern_list")

        # Apply modern button styling to toolbar buttons
        for btn_name in ['add_folder_btn', 'clear_clipboard_btn', 'ai_tag_btn', 'ai_filter_btn', 'filter_btn']:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                apply_modern_style(btn, self.theme_manager, "floating_toolbar")
                colors = self.theme_manager.get_current_theme()
                combined_style = f"""
                    QToolButton {{
                        background: {colors.bg_primary};
                        border: 1px solid {colors.border_normal};
                        border-radius: 8px;
                        font-size: 16px;
                        padding: 6px;
                        margin: 2px;
                        color: {colors.text_primary};
                    }}
                    QToolButton:hover {{
                        background: {colors.bg_hover};
                        border-color: {colors.border_focus};
                    }}
                    QToolButton:pressed {{
                        background: {colors.bg_pressed};
                    }}
                """
                btn.setStyleSheet(combined_style)

        # Apply list view styling
        if hasattr(self, 'asset_view'):
            list_style = self.theme_manager.get_stylesheet("list")
            self.asset_view.setStyleSheet(list_style)

        # Update separator colors
        theme_colors = self.theme_manager.get_current_theme()
        separator_style = f"color: {theme_colors.text_secondary}; font-size: 14px; margin: 0 4px;"

        # Apply to any separator widgets
        for child in self.findChildren(QLabel):
            if child.text() == "│":
                child.setStyleSheet(separator_style)

    def _create_filter_widgets(self):
        """Create filter control widgets"""
        self.star_filter = StarRatingFilter()
        self.type_filter_group = QButtonGroup(self)
        self.type_filter_group.setExclusive(True)

        # Style the filter buttons
        button_style = """
            QToolButton {
                background: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-height: 20px;
            }
            QToolButton:hover {
                background: #f8f9fa;
                border-color: #6c757d;
            }
            QToolButton:checked {
                background: #007bff;
                color: white;
                border-color: #0056b3;
            }
        """

        self.btn_all_filter = QToolButton(text="All", checkable=True, checked=True)
        self.btn_all_filter.setStyleSheet(button_style)

        self.btn_image_filter = QToolButton(text="📷 Images", checkable=True)
        self.btn_image_filter.setStyleSheet(button_style)

        self.btn_video_filter = QToolButton(text="🎬 Videos", checkable=True)
        self.btn_video_filter.setStyleSheet(button_style)

        for btn, type_name in [(self.btn_all_filter, "all"), (self.btn_image_filter, "image"),
                               (self.btn_video_filter, "video")]:
            btn.setProperty("type_name", type_name)
            self.type_filter_group.addButton(btn)

    def _connect_signals(self):
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.filter_btn.clicked.connect(self._show_filter_menu)
        self.clear_clipboard_btn.clicked.connect(lambda: self.commands.execute("assets.clear_clipboard"))
        self.ai_tag_btn.clicked.connect(self._show_ai_tagging_menu)
        self.ai_filter_btn.clicked.connect(self._show_ai_filter_menu)
        self.star_filter.filter_changed.connect(self._on_rating_filter_changed)
        self.type_filter_group.buttonClicked.connect(self._on_type_filter_changed)
        self.folder_tree.customContextMenuRequested.connect(self._folder_context_menu)
        self.folder_tree.selectionModel().selectionChanged.connect(self._on_folder_selected)
        self.asset_view.customContextMenuRequested.connect(self._asset_context_menu)
        self.asset_view.doubleClicked.connect(self._on_asset_double_clicked)
        self.asset_model.thumbnail_requested.connect(self._request_thumbnail_load)
        self.asset_delegate.rating_changed.connect(self._set_asset_rating)
        self.package_editor.package_saved.connect(self.refresh_folders)
        self.events.subscribe("assets:database_updated", self.refresh_folders)
        self.events.subscribe("assets:metadata_updated", self.refresh_folders)
        self.events.subscribe("ui:theme_changed", self._on_theme_changed)

        self.assets_loaded_signal.connect(self._on_assets_loaded_main_thread)
        self.thumbnail_loaded_signal.connect(self._on_thumbnail_loaded_main_thread)

    def _on_asset_double_clicked(self, index):
        if not index.isValid(): return
        preview = MediaPreviewWindow(self.framework, self.asset_model.get_all_assets(), index.row())
        self.pinned_previews.append(preview)
        preview.show()

    def _on_folder_selected(self, selected, deselected):
        if not selected.indexes():
            self.right_pane_stack.setCurrentWidget(self.asset_view)
            self.asset_model.clear()
            self.package_editor.load_package(None)
            return

        item_data = self.folder_model.data(selected.indexes()[0], Qt.ItemDataRole.UserRole)

        if isinstance(item_data, dict) and item_data.get("type") == "package":
            self.package_editor.load_package(item_data)
            self.right_pane_stack.setCurrentWidget(self.package_editor)
            self.current_folder = None
        else:
            self.right_pane_stack.setCurrentWidget(self.asset_view)
            if item_data == "__duplicates__":
                self.current_folder = "__duplicates__"
                self.asset_model.clear()
                worker = self.framework.get_service("worker_manager")
                asset_service = self.framework.get_service("asset_service")
                worker.submit(asset_service.find_duplicates, on_result=self._on_assets_loaded_worker)
            else:
                self.refresh_assets(item_data)

    def _on_rating_filter_changed(self, rating):
        self._rating_filter = rating
        self._apply_filters()

    def _on_type_filter_changed(self, button):
        self._type_filter = button.property("type_name")
        self._apply_filters()

    def _show_filter_menu(self):
        menu = QMenu(self)
        if self.theme_manager:
            menu.setStyleSheet(self.theme_manager.get_stylesheet("menu"))

        # Rating filter section
        rating_label = menu.addAction("⭐ Filter by Rating")
        rating_label.setEnabled(False)
        star_action = QWidgetAction(menu)
        star_action.setDefaultWidget(self.star_filter)
        menu.addAction(star_action)
        menu.addSeparator()

        # Type filter section
        type_label = menu.addAction("🎭 Filter by Type")
        type_label.setEnabled(False)

        type_filter_container = QWidget()
        type_filter_layout = QHBoxLayout(type_filter_container)
        type_filter_layout.setContentsMargins(8, 4, 8, 4)
        type_filter_layout.setSpacing(6)
        type_filter_layout.addWidget(self.btn_all_filter)
        type_filter_layout.addWidget(self.btn_image_filter)
        type_filter_layout.addWidget(self.btn_video_filter)

        type_action = QWidgetAction(menu)
        type_action.setDefaultWidget(type_filter_container)
        menu.addAction(type_action)

        # Show active filters status
        active_filters = []
        if self._rating_filter > 0:
            active_filters.append(f"Rating: {self._rating_filter}+ stars")
        if self._type_filter != "all":
            active_filters.append(f"Type: {self._type_filter}")
        if self._tag_filters:
            active_filters.append(f"AI Tags: {len(self._tag_filters)} layers")

        if active_filters:
            menu.addSeparator()
            status_label = menu.addAction(f"🔍 Active: {', '.join(active_filters)}")
            status_label.setEnabled(False)

        menu.exec(self.filter_btn.mapToGlobal(self.filter_btn.rect().bottomLeft()))

    def _show_ai_tagging_menu(self):
        """Show AI tagging options menu"""
        if not self.current_folder:
            QMessageBox.information(self, "AI Tagging", "Please select a folder first.")
            return

        menu = QMenu(self)
        menu.addAction("🚀 Quick AI Tags (Fast)").triggered.connect(
            lambda: self._run_ai_tagging(priority=1))
        menu.addAction("🎯 Standard AI Tags").triggered.connect(
            lambda: self._run_ai_tagging(priority=2))
        menu.addAction("🔬 Deep AI Analysis (Slow)").triggered.connect(
            lambda: self._run_ai_tagging(priority=3))
        menu.addSeparator()
        menu.addAction("⚙️ Configure AI Providers").triggered.connect(
            self._open_ai_settings)

        menu.exec(self.ai_tag_btn.mapToGlobal(self.ai_tag_btn.rect().bottomLeft()))

    def _show_ai_filter_menu(self):
        """Show AI tag filter menu"""
        menu = QMenu(self)

        # Get available tag layers
        tag_registry = self.framework.get_service("tag_layer_registry")
        if not tag_registry:
            menu.addAction("AI tag system not available")
            menu.exec(self.ai_filter_btn.mapToGlobal(self.ai_filter_btn.rect().bottomLeft()))
            return

        layers = tag_registry.list_layers()
        light_layers = [l for l in layers if l.get("processing_priority", 1) == 1]

        if not light_layers:
            menu.addAction("No AI tag layers available")
        else:
            menu.addAction("<b>Filter by AI Tags:</b>")
            menu.addSeparator()

            for layer in light_layers:
                layer_menu = QMenu(layer["name"], menu)

                # Get unique tag values for this layer
                tag_values = self._get_tag_values_for_layer(layer["id"])
                if tag_values:
                    for tag_value in sorted(tag_values)[:20]:  # Limit to 20 most common
                        action = layer_menu.addAction(tag_value)
                        action.setCheckable(True)
                        current_filters = self._tag_filters.get(layer["id"], [])
                        action.setChecked(tag_value in current_filters)
                        action.triggered.connect(
                            lambda checked, layer_id=layer["id"], value=tag_value:
                            self._toggle_tag_filter(layer_id, value, checked))
                else:
                    layer_menu.addAction("No tags available")

                menu.addMenu(layer_menu)

        menu.addSeparator()
        clear_action = menu.addAction("Clear All Filters")
        clear_action.triggered.connect(self._clear_tag_filters)

        menu.exec(self.ai_filter_btn.mapToGlobal(self.ai_filter_btn.rect().bottomLeft()))

    def _run_ai_tagging(self, priority):
        """Run AI tagging on current folder with specified priority"""
        if not self.current_folder:
            return

        asset_service = self.framework.get_service("asset_service")
        if asset_service:
            asset_service.run_ai_tagging_on_folder(self.current_folder, priority)
            priority_names = {1: "Quick", 2: "Standard", 3: "Deep"}
            self.log.notification(f"{priority_names.get(priority, '')} AI tagging started for current folder")

    def _get_tag_values_for_layer(self, layer_id):
        """Get unique tag values for a specific layer from current assets"""
        if not self._current_folder_assets:
            return []

        tag_registry = self.framework.get_service("tag_layer_registry")
        if not tag_registry:
            return []

        # Get all tags for current assets
        asset_ids = [a.id for a in self._current_folder_assets]
        session = self.db.get_session()
        try:
            from plugins.core.models import AssetTag
            tags = session.query(AssetTag.value).filter(
                AssetTag.layer_id == layer_id,
                AssetTag.asset_id.in_(asset_ids),
                AssetTag.value.isnot(None)
            ).distinct().all()
            return [tag[0] for tag in tags if tag[0]]
        finally:
            session.close()

    def _toggle_tag_filter(self, layer_id, tag_value, enabled):
        """Toggle a tag filter on/off"""
        if layer_id not in self._tag_filters:
            self._tag_filters[layer_id] = []

        if enabled and tag_value not in self._tag_filters[layer_id]:
            self._tag_filters[layer_id].append(tag_value)
        elif not enabled and tag_value in self._tag_filters[layer_id]:
            self._tag_filters[layer_id].remove(tag_value)

        # Clean up empty filters
        if not self._tag_filters[layer_id]:
            del self._tag_filters[layer_id]

        self._apply_filters()

    def _clear_tag_filters(self):
        """Clear all AI tag filters"""
        self._tag_filters = {}
        self._apply_filters()

    def _request_thumbnail_load(self, index, path, asset_id):
        if asset_id in self.thumbnail_cache:
            self.asset_model.cache_thumbnail(asset_id, self.thumbnail_cache[asset_id])
        elif asset_id not in self.thumbnail_queue:
            self.thumbnail_queue.add(asset_id)
            worker = self.framework.get_service("worker_manager")
            asset_service = self.framework.get_service("asset_service")
            worker.submit(asset_service.get_or_create_thumbnail,
                          on_result=lambda p: self._on_thumbnail_path_resolved_worker(asset_id, p),
                          path=path, file_hash=asset_id)

    def _on_thumbnail_path_resolved_worker(self, asset_id, thumb_path):
        if asset_id in self.thumbnail_queue: self.thumbnail_queue.remove(asset_id)
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                self.thumbnail_loaded_signal.emit(asset_id, pixmap)

    def _on_thumbnail_loaded_main_thread(self, asset_id, pixmap):
        self.thumbnail_cache[asset_id] = pixmap
        self.asset_model.cache_thumbnail(asset_id, pixmap)

    def _asset_context_menu(self, position):
        if not (index := self.asset_view.indexAt(position)).isValid(): return
        path = self.asset_model.data(index, Qt.ItemDataRole.UserRole)["path"]
        menu = QMenu()
        if self.current_folder == "__duplicates__":
            menu.addAction("🔥 Delete File from Disk").triggered.connect(lambda: self._delete_duplicate_asset(path))
            menu.addSeparator()
        menu.addAction("Send to Input 1").triggered.connect(lambda: self.events.publish("preview:send_to_input",
                                                                                        event_data=(
                                                                                            "preview:send_to_input",
                                                                                            {"target": 1,
                                                                                             "path": path})))
        menu.addAction("Send to Input 2").triggered.connect(lambda: self.events.publish("preview:send_to_input",
                                                                                        event_data=(
                                                                                            "preview:send_to_input",
                                                                                            {"target": 2,
                                                                                             "path": path})))
        menu.addSeparator()

        # AI Tagging submenu
        ai_menu = QMenu("AI Analysis", menu)
        asset_data = self.asset_model.data(index, Qt.ItemDataRole.UserRole)
        asset_id = asset_data.get("id") if asset_data else None

        if asset_id:
            ai_menu.addAction("🔬 Run Deep Analysis").triggered.connect(
                lambda: self._run_deep_analysis_on_asset(asset_id))
            ai_menu.addAction("🏷️ Show AI Tags").triggered.connect(
                lambda: self._show_asset_tags(asset_id))
        else:
            ai_menu.addAction("Asset ID not available")

        menu.addMenu(ai_menu)
        menu.exec(self.asset_view.mapToGlobal(position))

    def _run_deep_analysis_on_asset(self, asset_id):
        """Run deep AI analysis on a single asset"""
        asset_service = self.framework.get_service("asset_service")
        if asset_service:
            asset_service.run_deep_ai_analysis([asset_id])
            self.log.notification("Deep AI analysis started for selected asset")

    def _show_asset_tags(self, asset_id):
        """Show all AI tags for an asset"""
        tag_registry = self.framework.get_service("tag_layer_registry")
        if not tag_registry:
            QMessageBox.information(self, "AI Tags", "AI tag system not available")
            return

        tags = tag_registry.list_asset_tags(asset_id)
        if not tags:
            QMessageBox.information(self, "AI Tags", "No AI tags found for this asset.\n\nTry running AI analysis first.")
            return

        # Group tags by layer
        layer_tags = {}
        for tag in tags:
            layer_id = tag["layer_id"]
            if layer_id not in layer_tags:
                layer_tags[layer_id] = []
            layer_tags[layer_id].append(tag)

        # Format tags for display
        message = "AI Tags for this asset:\n\n"
        layers = tag_registry.list_layers()
        layer_names = {l["id"]: l["name"] for l in layers}

        for layer_id, layer_tag_list in layer_tags.items():
            layer_name = layer_names.get(layer_id, layer_id)
            message += f"📋 {layer_name}:\n"

            for tag in layer_tag_list:
                value = tag.get("value") or tag.get("text_value") or str(tag.get("numeric_value", ""))
                confidence = tag.get("confidence", 0)
                source = tag.get("source", "AI")

                if confidence and confidence < 1.0:
                    message += f"  • {value} ({confidence:.1%} confidence, {source})\n"
                else:
                    message += f"  • {value} ({source})\n"
            message += "\n"

        QMessageBox.information(self, "AI Tags", message)

    def _open_ai_settings(self):
        """Open AI provider settings dialog"""
        dialog = AIProviderSettingsDialog(self.framework, self)
        dialog.exec()

    def _on_theme_changed(self, **kwargs):
        """Handle theme change events"""
        self._apply_theme()

    def _folder_context_menu(self, position):
        index = self.folder_tree.indexAt(position)
        if not index.isValid() or not index.parent().isValid():
            menu = QMenu()
            menu.addAction("Create New Asset Package...").triggered.connect(self._create_new_package)
            menu.exec(self.folder_tree.mapToGlobal(position))
            return

        data = self.folder_model.data(index, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("type") == "package":
            menu = QMenu()
            menu.addAction("Scan Package for Assets").triggered.connect(
                lambda: self.commands.execute("assets.resync_emotion_packages", package_uuid=data['uuid']))
            menu.addAction("Delete Package").triggered.connect(lambda: self.log.info(f"Deleting {data['name']}..."))
            menu.exec(self.folder_tree.mapToGlobal(position))
            return

        folder_path = data
        if folder_path in self.settings.get("library_folders", []):
            menu = QMenu()
            menu.addAction("Remove From Library").triggered.connect(lambda: self.remove_folder(folder_path))
            menu.exec(self.folder_tree.mapToGlobal(position))

    def _create_new_package(self):
        dialog = CreatePackageDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            if not name:
                QMessageBox.warning(self, "Create Package", "A package name is required.")
                return

            project_root = self.framework.get_project_root()
            packages_dir = os.path.join(project_root, "packages")
            os.makedirs(packages_dir, exist_ok=True)

            package_folder_name = name.lower().replace(" ", "_").strip()
            package_path = os.path.join(packages_dir, package_folder_name)

            if os.path.exists(package_path):
                QMessageBox.warning(self, "Create Package", "A package folder with this name already exists.")
                return

            try:
                os.makedirs(package_path)
                manifest_path = os.path.join(package_path, "asset.json")

                new_manifest = {
                    "uuid": str(uuid.uuid4()),
                    "type": "emotion_package",
                    "name": name,
                    "version": "1.0.0",
                    "intents": {},
                    "scan_rules": []
                }
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(new_manifest, f, indent=2)

                self.log.notification(f"Asset package '{name}' created at '{package_path}'.")
                asset_dirs_to_scan = [packages_dir] + self.settings.get("library_folders", [])
                self.asset_manager.discover(asset_dirs=asset_dirs_to_scan)
                self.refresh_folders()
            except Exception as e:
                self.log.error(f"Failed to create new asset package: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Could not create package: {e}")

    def _set_asset_rating(self, asset_id, rating):
        if asset_service := self.framework.get_service("asset_service"):
            asset_service.set_asset_rating(asset_id, rating)

    def _delete_duplicate_asset(self, path):
        if asset_service := self.framework.get_service("asset_service"):
            asset_service.delete_asset_by_path(path)

    def remove_folder(self, folder_path):
        library_folders = self.settings.get("library_folders", [])
        if folder_path in library_folders:
            library_folders.remove(folder_path)
            self.settings.set("library_folders", library_folders)
            self.refresh_folders()
            if self.current_folder == folder_path:
                self.current_folder = None
                self.asset_model.clear()

    def add_folder(self):
        if folder_path := QFileDialog.getExistingDirectory(self, "Select Library Folder"):
            library_folders = self.settings.get("library_folders", [])
            if folder_path not in library_folders:
                library_folders.append(folder_path)
                self.settings.set("library_folders", library_folders)
                self.refresh_folders()
            self.commands.execute("assets.scan_folder", folder_path=folder_path)

    def save_state(self) -> dict:
        if selected := self.folder_tree.selectionModel().selectedIndexes():
            return {"selected_folder": self.folder_model.data(selected[0], Qt.ItemDataRole.UserRole)}
        return {}

    def restore_state(self, state: dict):
        if folder_data := state.get("selected_folder"):
            for row in range(self.folder_model.rowCount()):
                parent_index = self.folder_model.index(row, 0)
                for child_row in range(self.folder_model.rowCount(parent_index)):
                    child_index = self.folder_model.index(child_row, 0, parent_index)
                    if self.folder_model.data(child_index, Qt.ItemDataRole.UserRole) == folder_data:
                        self.folder_tree.setCurrentIndex(child_index)
                        return

    def refresh_folders(self):
        self.folder_model.clear()
        packages_root = QStandardItem("📦 Asset Packages")
        packages_root.setEditable(False)
        self.folder_model.appendRow(packages_root)

        if self.asset_manager:
            packages = self.asset_manager.emotion_packages or {}
            for pkg_uuid, manifest in sorted(packages.items(), key=lambda item: item[1].name):
                item = QStandardItem(manifest.name or "Unnamed Package")
                item.setData({"type": "package", "uuid": pkg_uuid, "name": manifest.name, "path": manifest.path}, Qt.ItemDataRole.UserRole)
                packages_root.appendRow(item)

        folders_root = QStandardItem("📁 Library Folders")
        folders_root.setEditable(False)
        self.folder_model.appendRow(folders_root)

        output_dir = self.settings.get("output_directory", "generated_media")
        generated_item = QStandardItem("✨ Generated")
        generated_item.setData(output_dir, Qt.ItemDataRole.UserRole)
        folders_root.appendRow(generated_item)

        clipboard_item = QStandardItem("📋 Clipboard")
        clipboard_item.setData("__clipboard__", Qt.ItemDataRole.UserRole)
        folders_root.appendRow(clipboard_item)

        duplicates_item = QStandardItem("⚠️ Duplicates")
        duplicates_item.setData("__duplicates__", Qt.ItemDataRole.UserRole)
        folders_root.appendRow(duplicates_item)

        library_folders = self.settings.get("library_folders", [])
        for folder in sorted(library_folders):
            item = QStandardItem(os.path.basename(folder))
            item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
            item.setData(folder, Qt.ItemDataRole.UserRole)
            folders_root.appendRow(item)

        self.folder_tree.expandAll()

    def refresh_assets(self, folder_path=None):
        self.current_folder = folder_path
        self.asset_model.clear()
        if folder_path:
            actual_folder = folder_path
            if folder_path == "__clipboard__":
                actual_folder = self.settings.resolve_user_path("clipboard", ensure_exists=False)
            elif not os.path.isabs(folder_path):
                actual_folder = self.settings.resolve_user_path(folder_path, ensure_exists=False)
            worker = self.framework.get_service("worker_manager")
            worker.submit(self.db.query, on_result=self._on_assets_loaded_worker,
                          model=Asset, filter_func=lambda a: a.path.startswith(actual_folder))

    def _on_assets_loaded_worker(self, assets):
        self.assets_loaded_signal.emit(assets)

    def _on_assets_loaded_main_thread(self, assets):
        self._current_folder_assets = assets
        self._apply_filters()

    def _apply_filters(self):
        filtered = self._current_folder_assets

        # Apply rating filter
        if self._rating_filter > 0:
            filtered = [a for a in filtered if a.rating >= self._rating_filter]

        # Apply type filter
        if self._type_filter != "all":
            filtered = [a for a in filtered if a.asset_type.value == self._type_filter]

        # Apply AI tag filters
        if self._tag_filters:
            filtered = self._apply_tag_filters(filtered)

        self.asset_model.set_assets(filtered)

    def _apply_tag_filters(self, assets):
        """Apply AI tag filters to asset list"""
        if not self._tag_filters:
            return assets

        session = self.db.get_session()
        try:
            from plugins.core.models import AssetTag
            filtered_assets = []

            for asset in assets:
                asset_matches = True

                # Asset must match ALL active filter groups (AND logic between layers)
                for layer_id, required_tags in self._tag_filters.items():
                    if not required_tags:
                        continue

                    # Get asset's tags for this layer
                    asset_tags = session.query(AssetTag.value).filter(
                        AssetTag.asset_id == asset.id,
                        AssetTag.layer_id == layer_id,
                        AssetTag.value.isnot(None)
                    ).all()
                    asset_tag_values = [tag[0] for tag in asset_tags]

                    # Asset must have at least one of the required tags for this layer (OR logic within layer)
                    layer_match = any(tag in asset_tag_values for tag in required_tags)
                    if not layer_match:
                        asset_matches = False
                        break

                if asset_matches:
                    filtered_assets.append(asset)

            return filtered_assets
        finally:
            session.close()

