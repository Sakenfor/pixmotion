# D:/My Drive/code/pixmotion/plugins/assets/browser.py
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
    QDialog,
    QLineEdit,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QStackedWidget,
    QPushButton,
)
from PyQt6.QtCore import Qt, QSize, QModelIndex, QTimer, QItemSelectionModel, pyqtSignal
from PyQt6.QtGui import QIcon, QStandardItemModel, QStandardItem, QPixmap

from plugins.core.models import Asset
from .views import AssetModel, AssetDelegate
from .widgets import AssetHoverManager, StarRatingFilter
from .windows import MediaPreviewWindow
from framework.manifests import EmotionPackageManifest
from .package_editor import PackageEditorWidget


class CreatePackageDialog(QDialog):
    """Dialog to get the name for a new asset package."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Asset Package")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., NPC Greeting Animations")
        layout.addRow("Package Name:", self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_name(self):
        return self.name_edit.text().strip()


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

        self._current_folder_assets = []
        self._rating_filter = 0
        self._type_filter = "all"

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
        header_bar = QWidget()
        header_bar.setMaximumHeight(32)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(5, 0, 5, 0)
        header_layout.setSpacing(6)
        header_layout.addWidget(QLabel("<b>Asset Browser</b>"))
        header_layout.addStretch()
        self.filter_btn = QToolButton(icon=self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
                                      toolTip="Filter assets")
        header_layout.addWidget(self.filter_btn)
        self.add_folder_btn = QToolButton(icon=self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
                                          toolTip="Add Library Folder")
        header_layout.addWidget(self.add_folder_btn)
        self.clear_clipboard_btn = QToolButton(
            icon=self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton),
            toolTip="Clear all assets from the clipboard folder")
        header_layout.addWidget(self.clear_clipboard_btn)
        self.star_filter = StarRatingFilter()
        self.type_filter_group = QButtonGroup(self)
        self.type_filter_group.setExclusive(True)
        self.btn_all_filter = QToolButton(text="All", checkable=True, checked=True)
        self.btn_image_filter = QToolButton(icon=self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon),
                                            checkable=True)
        self.btn_video_filter = QToolButton(icon=self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay),
                                            checkable=True)
        for btn, type_name in [(self.btn_all_filter, "all"), (self.btn_image_filter, "image"),
                               (self.btn_video_filter, "video")]:
            btn.setProperty("type_name", type_name)
            self.type_filter_group.addButton(btn)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        self.folder_tree = QTreeView()
        self.folder_tree.setModel(self.folder_model)
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        left_layout.addWidget(self.folder_tree)

        self.right_pane_stack = QStackedWidget()

        self.asset_view = QListView()
        self.asset_view.setModel(self.asset_model)
        self.asset_view.setViewMode(QListView.ViewMode.IconMode)
        self.asset_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.asset_view.setSpacing(6)
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

        self.package_editor = PackageEditorWidget(self.framework)

        self.right_pane_stack.addWidget(self.asset_view)
        self.right_pane_stack.addWidget(self.package_editor)

        splitter.addWidget(left_pane)
        splitter.addWidget(self.right_pane_stack)
        splitter.setSizes([250, 550])
        layout.addWidget(header_bar)
        layout.addWidget(splitter, 1)

    def _connect_signals(self):
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.filter_btn.clicked.connect(self._show_filter_menu)
        self.clear_clipboard_btn.clicked.connect(lambda: self.commands.execute("assets.clear_clipboard"))
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
        star_action = QWidgetAction(menu)
        star_action.setDefaultWidget(self.star_filter)
        menu.addAction("<b>Rating:</b>")
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
        menu.exec(self.asset_view.mapToGlobal(position))

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
                    "type": "emotion_package",  # Default type, can be changed in editor
                    "name": name,
                    "version": "1.0.0",
                    "intents": {},
                    "scan_rules": []
                }
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(new_manifest, f, indent=2)

                self.log.notification(f"Asset package '{name}' created at '{package_path}'.")

                # Rescan all asset directories to find the new package manifest
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
                item.setData({
                    "type": "package",
                    "uuid": pkg_uuid,
                    "name": manifest.name,
                    "path": manifest.path
                }, Qt.ItemDataRole.UserRole)
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
            worker = self.framework.get_service("worker_manager")
            worker.submit(self.db.query, on_result=self._on_assets_loaded_worker,
                          model=Asset, filter_func=lambda a: a.path.startswith(folder_path))

    def _on_assets_loaded_worker(self, assets):
        """Callback for when assets are loaded. Emits a signal to update UI on main thread."""
        self.assets_loaded_signal.emit(assets)

    def _on_assets_loaded_main_thread(self, assets):
        """Slot that receives loaded assets and safely updates the UI."""
        self._current_folder_assets = assets
        self._apply_filters()

    def _apply_filters(self):
        filtered = self._current_folder_assets
        if self._rating_filter > 0:
            filtered = [a for a in filtered if a.rating >= self._rating_filter]
        if self._type_filter != "all":
            filtered = [a for a in filtered if a.asset_type.value == self._type_filter]
        self.asset_model.set_assets(filtered)

