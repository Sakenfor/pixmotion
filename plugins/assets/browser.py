# D:/My Drive/code/pixmotion/plugins/assets/browser.py
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeView, QToolButton,
                             QListView, QFileDialog, QSplitter, QMenu, QStyle,
                             QHBoxLayout, QLabel, QButtonGroup, QWidgetAction)
from PyQt6.QtCore import (Qt, QSize, QModelIndex, QTimer)
from PyQt6.QtGui import (QIcon, QStandardItemModel, QStandardItem, QPixmap)

from core.models import Asset
from .views import AssetModel, AssetDelegate
from .widgets import AssetHoverManager, StarRatingFilter
from .windows import MediaPreviewWindow


class AssetBrowserPanel(QWidget):
    """A panel for browsing the asset library with a custom title bar."""

    def __init__(self, framework):
        super().__init__()
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.settings = framework.get_service("settings_service")
        self.events = framework.get_service("event_manager")
        self.db = framework.get_service("database_service")
        self.commands = framework.get_service("command_manager")

        # State for filtering
        self._current_folder_assets = []
        self._rating_filter = 0
        self._type_filter = 'all'

        self.thumbnail_queue = set()
        self.thumbnail_cache = {}
        self.folder_model = QStandardItemModel()
        self.asset_model = AssetModel(self.log)
        self.pinned_previews = []
        self.current_folder = None

        self._init_ui()
        self._connect_signals()
        self.refresh_folders()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Header Bar with Title and Filters ---
        header_bar = QWidget()
        header_bar.setMaximumHeight(32)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(5, 0, 5, 0)
        header_layout.setSpacing(6)

        header_layout.addWidget(QLabel("<b>Asset Browser</b>"))
        header_layout.addStretch()

        # --- Filter Controls (moved to header) ---
        self.filter_btn = QToolButton()
        self.filter_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.filter_btn.setToolTip("Filter assets")
        header_layout.addWidget(self.filter_btn)

        self.add_folder_btn = QToolButton()
        self.add_folder_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.add_folder_btn.setToolTip("Add Library Folder")
        header_layout.addWidget(self.add_folder_btn)

        self.clear_clipboard_btn = QToolButton()
        self.clear_clipboard_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.clear_clipboard_btn.setToolTip("Clear all assets from the clipboard folder")
        header_layout.addWidget(self.clear_clipboard_btn)

        # Create the filter widgets, but don't add them to the layout directly
        self.star_filter = StarRatingFilter()
        self.type_filter_group = QButtonGroup(self)
        self.type_filter_group.setExclusive(True)
        self.btn_all_filter = QToolButton()
        self.btn_all_filter.setText("All")
        self.btn_all_filter.setCheckable(True)
        self.btn_all_filter.setChecked(True)
        self.btn_image_filter = QToolButton()
        self.btn_image_filter.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_image_filter.setCheckable(True)
        self.btn_video_filter = QToolButton()
        self.btn_video_filter.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_video_filter.setCheckable(True)
        for btn, type_name in [(self.btn_all_filter, 'all'), (self.btn_image_filter, 'image'), (self.btn_video_filter, 'video')]:
            btn.setProperty("type_name", type_name)
            self.type_filter_group.addButton(btn)

        # --- Main Content Splitter ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Pane (Folders)
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        self.folder_tree = QTreeView()
        self.folder_tree.setModel(self.folder_model)
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        left_layout.addWidget(self.folder_tree)

        # Asset View
        self.asset_view = QListView()
        self.asset_view.setModel(self.asset_model)
        self.asset_view.setViewMode(QListView.ViewMode.IconMode)
        self.asset_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.asset_view.setGridSize(QSize(128, 128 + 15))
        self.asset_view.setSpacing(5)
        self.asset_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.asset_view.setMouseTracking(True)
        self.asset_view.setUniformItemSizes(True)

        self.asset_delegate = AssetDelegate(self)
        self.asset_view.setItemDelegate(self.asset_delegate)

        self.hover_manager = AssetHoverManager(self.asset_view)
        self.asset_view.viewport().installEventFilter(self.hover_manager)

        splitter.addWidget(left_pane)
        splitter.addWidget(self.asset_view)
        splitter.setSizes([200, 400])

        layout.addWidget(header_bar)
        layout.addWidget(splitter, 1)

    def _connect_signals(self):
        # Connect signals from the header bar
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.filter_btn.clicked.connect(self._show_filter_menu)
        self.clear_clipboard_btn.clicked.connect(lambda: self.commands.execute("assets.clear_clipboard"))

        # Connect signals from the filter widgets
        self.star_filter.filter_changed.connect(self._on_rating_filter_changed)
        self.type_filter_group.buttonClicked.connect(self._on_type_filter_changed)

        # Connect signals from the views
        self.folder_tree.customContextMenuRequested.connect(self._folder_context_menu)
        self.folder_tree.selectionModel().selectionChanged.connect(self._on_folder_selected)
        self.asset_view.customContextMenuRequested.connect(self._asset_context_menu)
        self.asset_view.doubleClicked.connect(self._on_asset_double_clicked)
        self.asset_model.thumbnail_requested.connect(self._request_thumbnail_load)
        self.asset_delegate.rating_changed.connect(self._set_asset_rating)

        # Connect framework events
        self.events.subscribe("assets:database_updated", lambda **kwargs: self.refresh_assets(self.current_folder))
        self.events.subscribe("assets:metadata_updated", lambda **kwargs: self.refresh_assets(self.current_folder))

    def _on_asset_double_clicked(self, index):
        if not index.isValid():
            return
        preview = MediaPreviewWindow(self.framework, self.asset_model.get_all_assets(), index.row())
        self.pinned_previews.append(preview)
        preview.show()

    def _on_folder_selected(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes:
            return

        folder_identifier = self.folder_model.data(indexes[0], Qt.ItemDataRole.UserRole)
        if folder_identifier == "__clipboard__":
            clipboard_dir = os.path.join(self.framework.get_project_root(), "assets", "clipboard")
            self.refresh_assets(clipboard_dir)
        elif folder_identifier == "__duplicates__":
            self.current_folder = "__duplicates__"
            self.asset_model.clear()
            self.log.info("Finding duplicate assets...")
            worker = self.framework.get_service("worker_manager")
            asset_service = self.framework.get_service("asset_service")
            worker.submit(
                asset_service.find_duplicates,
                on_result=self._on_assets_loaded
            )
        elif folder_identifier == "__pinterest__":
            pinterest_dir = os.path.join(self.framework.get_project_root(), "assets", "pinterest")
            os.makedirs(pinterest_dir, exist_ok=True)
            self.refresh_assets(pinterest_dir)
        else:
            self.refresh_assets(folder_identifier)

    def _on_rating_filter_changed(self, rating):
        self._rating_filter = rating
        self.log.info(f"Rating filter changed to: {rating}")
        self._apply_filters()

    def _on_type_filter_changed(self, button):
        type_name = button.property("type_name")
        self._type_filter = type_name
        self.log.info(f"Type filter changed to: {type_name}")
        self._apply_filters()

    def _show_filter_menu(self):
        """Creates and displays a popup menu containing the filter widgets."""
        menu = QMenu(self)

        star_label = QLabel("<b>Rating:</b>")
        star_label.setContentsMargins(5, 2, 5, 2)
        star_action = QWidgetAction(menu)
        star_action.setDefaultWidget(self.star_filter)
        menu.addAction(star_label.text())
        menu.addAction(star_action)

        menu.addSeparator()

        type_filter_container = QWidget()
        type_filter_layout = QHBoxLayout(type_filter_container)
        type_filter_layout.setContentsMargins(5, 2, 5, 2)
        type_filter_layout.addWidget(self.btn_all_filter)
        type_filter_layout.addWidget(self.btn_image_filter)
        type_filter_layout.addWidget(self.btn_video_filter)
        type_action = QWidgetAction(menu)
        type_action.setDefaultWidget(type_filter_container)
        menu.addAction(type_action)

        menu.exec(self.filter_btn.mapToGlobal(self.filter_btn.rect().bottomLeft()))

    def _request_thumbnail_load(self, index, path, asset_id):
        """Queues a path for thumbnail loading if it's not already queued."""
        if asset_id in self.thumbnail_cache:
            self.asset_model.cache_thumbnail(asset_id, self.thumbnail_cache[asset_id])
        elif asset_id not in self.thumbnail_queue:
            self.thumbnail_queue.add(asset_id)
            worker = self.framework.get_service("worker_manager")
            asset_service = self.framework.get_service("asset_service")
            worker.submit(
                asset_service.get_or_create_thumbnail,
                on_result=lambda thumb_path: self._on_thumbnail_path_resolved(index, asset_id, thumb_path),
                path=path,
                file_hash=asset_id
            )

    def _on_thumbnail_path_resolved(self, index, asset_id, thumb_path):
        """Once we have the path, load the pixmap and force an update."""
        if asset_id in self.thumbnail_queue:
            self.thumbnail_queue.remove(asset_id)

        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                self.thumbnail_cache[asset_id] = pixmap
                self.asset_model.cache_thumbnail(asset_id, pixmap)

    def _asset_context_menu(self, position):
        index = self.asset_view.indexAt(position)
        if not index.isValid():
            return

        asset_data = self.asset_model.data(index, Qt.ItemDataRole.UserRole)
        path = asset_data['path']

        menu = QMenu()

        if self.current_folder == "__duplicates__":
            delete_action = menu.addAction("🔥 Delete File from Disk")
            delete_action.triggered.connect(lambda: self._delete_duplicate_asset(path))
            menu.addSeparator()

        send_to_input1 = menu.addAction("Send to Input 1")
        send_to_input2 = menu.addAction("Send to Input 2")
        action = menu.exec(self.asset_view.mapToGlobal(position))

        if action == send_to_input1:
            self.events.publish("preview:send_to_input", event_data=("preview:send_to_input", {"target": 1, "path": path}))
        elif action == send_to_input2:
            self.events.publish("preview:send_to_input", event_data=("preview:send_to_input", {"target": 2, "path": path}))

    def _folder_context_menu(self, position):
        index = self.folder_tree.indexAt(position)
        if not index.isValid():
            return

        folder_path = index.data(Qt.ItemDataRole.UserRole)
        output_dir = self.settings.get("output_directory", "generated_media")
        if folder_path == output_dir or (isinstance(folder_path, str) and folder_path.startswith("__")): return

        menu = QMenu()
        library_folders = self.settings.get("library_folders", [])
        if folder_path in library_folders:
            remove_action = menu.addAction("Remove From Library")
            action = menu.exec(self.folder_tree.mapToGlobal(position))

            if action == remove_action:
                self.remove_folder(folder_path)

    def _set_asset_rating(self, asset_id, rating):
        """Calls the asset service to update the rating."""
        asset_service = self.framework.get_service("asset_service")
        if asset_service:
            asset_service.set_asset_rating(asset_id, rating)

    def _delete_duplicate_asset(self, path):
        """Calls the asset service to delete a specific duplicate file."""
        asset_service = self.framework.get_service("asset_service")
        if asset_service:
            asset_service.delete_asset_by_path(path)

    def remove_folder(self, folder_path):
        """Removes a folder from the library folders setting."""
        library_folders = self.settings.get("library_folders", [])
        if folder_path in library_folders:
            library_folders.remove(folder_path)
            self.settings.set("library_folders", library_folders)
            self.refresh_folders()
            if self.current_folder == folder_path:
                self.current_folder = None
                self.refresh_assets(None)

    def add_folder(self):
        """Opens a dialog to add a new folder to the library."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Library Folder")
        if folder_path:
            library_folders = self.settings.get("library_folders", [])
            if folder_path not in library_folders:
                library_folders.append(folder_path)
                self.settings.set("library_folders", library_folders)
                self.refresh_folders()
            self.commands.execute("assets.scan_folder", folder_path=folder_path)

    def save_state(self) -> dict:
        """Saves the currently selected folder path."""
        selected_indexes = self.folder_tree.selectionModel().selectedIndexes()
        if selected_indexes and self.folder_model.rowCount() > 0:
            folder_path = self.folder_model.data(selected_indexes[0], Qt.ItemDataRole.UserRole)
            return {"selected_folder": folder_path}
        return {}

    def restore_state(self, state: dict):
        """Restores the folder selection from a saved state."""
        folder_path = state.get("selected_folder")
        if not folder_path:
            return
        for row in range(self.folder_model.rowCount()):
            index = self.folder_model.index(row, 0)
            if self.folder_model.data(index, Qt.ItemDataRole.UserRole) == folder_path:
                self.folder_tree.selectionModel().clear()
                self.folder_tree.setCurrentIndex(index)
                self.folder_tree.scrollTo(index)
                return
        self.log.warning(f"Could not find saved folder path in model: {folder_path}")

    def refresh_folders(self):
        """Clears and re-populates the folder view from settings."""
        self.folder_model.clear()

        output_dir = self.settings.get("output_directory", "generated_media")
        generated_item = QStandardItem("✨ Generated")
        generated_item.setData(output_dir, Qt.ItemDataRole.UserRole)
        self.folder_model.appendRow(generated_item)

        clipboard_item = QStandardItem("📋 Clipboard")
        clipboard_item.setData("__clipboard__", Qt.ItemDataRole.UserRole)
        self.folder_model.appendRow(clipboard_item)
        duplicates_item = QStandardItem("⚠️ Duplicates")
        duplicates_item.setData("__duplicates__", Qt.ItemDataRole.UserRole)
        self.folder_model.appendRow(duplicates_item)

        pinterest_item = QStandardItem("📌 Pinterest")
        pinterest_item.setData("__pinterest__", Qt.ItemDataRole.UserRole)
        self.folder_model.appendRow(pinterest_item)

        library_folders = self.settings.get("library_folders", [])
        for folder in sorted(library_folders):
            item = QStandardItem(os.path.basename(folder))
            item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
            item.setData(folder, Qt.ItemDataRole.UserRole)
            self.folder_model.appendRow(item)

    def refresh_assets(self, folder_path=None):
        self.current_folder = folder_path
        self._current_folder_assets = []
        self.thumbnail_cache.clear()
        self.asset_model.clear()
        self.thumbnail_queue.clear()

        if folder_path:
            worker = self.framework.get_service("worker_manager")
            worker.submit(
                self.db.query,
                on_result=self._on_assets_loaded,
                model=Asset,
                filter_func=lambda a: a.path.startswith(folder_path)
            )

    def _on_assets_loaded(self, assets):
        """Callback for when assets are loaded from the database."""
        self._current_folder_assets = assets
        self._apply_filters()

    def _apply_filters(self):
        """Filters the currently loaded assets and updates the view."""
        filtered_assets = self._current_folder_assets
        if self._rating_filter > 0:
            filtered_assets = [asset for asset in filtered_assets if asset.rating >= self._rating_filter]
        if self._type_filter != 'all':
            filtered_assets = [asset for asset in filtered_assets if asset.asset_type == self._type_filter]
        self.asset_model.set_assets(filtered_assets)

        # --- DEFINITIVE FIX: Force a full layout recalculation by resetting the view's internal state. ---
        # This is scheduled with a zero-delay timer to run after the current event processing is complete,
        # ensuring the view has acknowledged the model reset before the relayout is forced.
        QTimer.singleShot(0, self.asset_view.reset)