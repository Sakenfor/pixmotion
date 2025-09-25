# D:/My Drive/code/pixmotion/plugins/assets/services.py
import os
import hashlib
from PIL import Image, ImageOps
import cv2

from plugins.core.models import Asset, AssetType


class AssetService:
    """
    A service for managing and scanning media assets.
    This service contains the business logic and delegates database
    operations to the AssetRepository.
    """

    SUPPORTED_TYPES = [".png", ".jpg", ".jpeg", ".mp4", ".mov", ".avi", ".webm", ".mkv"]
    THUMBNAIL_SIZE = (128, 128)

    def __init__(self, framework, repository):
        self.framework = framework
        self.repository = repository
        self.log = framework.get_service("log_manager")
        self.events = framework.get_service("event_manager")
        self.settings = framework.get_service("settings_service")
        self.events.subscribe("shell:ready", self._initial_scan)

    def set_asset_rating(self, asset_id, rating):
        if not asset_id or rating not in range(0, 6):
            return
        if self.repository.update_rating(asset_id, rating):
            self.events.publish("assets:metadata_updated")

    def get_or_create_thumbnail(self, path, file_hash):
        return self._create_thumbnail(path, file_hash)

    def get_asset_path(self, asset_id: str) -> str | None:
        return self.repository.get_path_by_id(asset_id)

    def clear_clipboard_assets(self):
        clipboard_dir = self.settings.resolve_user_path("clipboard", ensure_exists=False)
        if not os.path.isdir(clipboard_dir):
            self.log.info("Clipboard folder does not exist; nothing to clear.")
            return

        clipboard_assets = self.repository.get_assets_in_clipboard(clipboard_dir)
        if not clipboard_assets:
            self.log.notification("Clipboard is already empty.")
            return

        for asset in clipboard_assets:
            if os.path.exists(asset.path):
                os.remove(asset.path)
            if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
                os.remove(asset.thumbnail_path)

        self.repository.delete_many(clipboard_assets)
        self.log.notification(
            f"Cleared {len(clipboard_assets)} assets from the clipboard."
        )
        self.events.publish("assets:database_updated")

    def delete_asset_by_path(self, path: str):
        # Publish a cancellable event before deleting
        event_data = {"path": path, "is_cancelled": False}
        self.events.publish_chain("assets:before_delete", event_data)

        if event_data["is_cancelled"]:
            self.log.notification(
                f"Deletion cancelled for {os.path.basename(path)} by a plugin."
            )
            return

        deleted_asset = self.repository.delete_by_path(path)
        if deleted_asset:
            if deleted_asset.thumbnail_path and os.path.exists(
                deleted_asset.thumbnail_path
            ):
                os.remove(deleted_asset.thumbnail_path)
            if os.path.exists(deleted_asset.path):
                os.remove(deleted_asset.path)

            self.log.notification(f"Deleted asset and file: {os.path.basename(path)}")
            self.events.publish("assets:database_updated")
        else:
            self.log.warning(f"Asset not in DB, but requested delete: {path}")

    def find_duplicates(self):
        return self.repository.find_duplicates()

    def run_ai_tagging_on_folder(self, folder_path, priority_level=1):
        """Run AI tagging on all assets in a folder"""
        def tagging_task():
            try:
                # Get all assets in the folder
                actual_folder = folder_path
                if folder_path == "__clipboard__":
                    actual_folder = self.settings.resolve_user_path("clipboard", ensure_exists=False)
                elif not os.path.isabs(folder_path):
                    actual_folder = self.settings.resolve_user_path(folder_path, ensure_exists=False)

                if not os.path.isdir(actual_folder):
                    self.log.warning(f"Folder not found for AI tagging: {actual_folder}")
                    return

                # Query assets from the database
                db_service = self.framework.get_service("database_service")
                from plugins.core.models import Asset

                session = db_service.get_session()
                try:
                    assets = session.query(Asset).filter(Asset.path.startswith(actual_folder)).all()
                    asset_data = [{"id": a.id, "path": a.path} for a in assets]

                    if not asset_data:
                        self.log.info(f"No assets found in folder: {folder_path}")
                        return

                    self.log.info(f"Starting AI tagging for {len(asset_data)} assets in {folder_path} (priority {priority_level})")

                    tag_runner = self.framework.get_service("tag_layer_runner")
                    if tag_runner:
                        tag_runner.run_layers_for_assets(asset_data, priority_filter=priority_level)
                        self.events.publish("assets:bulk_tags_updated", folder=folder_path, count=len(asset_data))
                        self.log.notification(f"AI tagging completed for {len(asset_data)} assets")
                    else:
                        self.log.warning("Tag layer runner service not available")
                finally:
                    session.close()
            except Exception as e:
                self.log.error(f"Failed to run AI tagging on folder {folder_path}: {e}", exc_info=True)

        worker = self.framework.get_service("worker_manager")
        worker.submit(tagging_task)

    def run_deep_ai_analysis(self, asset_ids):
        """Run deep AI analysis (priority 3) on specific assets"""
        def deep_analysis_task():
            try:
                db_service = self.framework.get_service("database_service")
                from plugins.core.models import Asset

                session = db_service.get_session()
                try:
                    assets = session.query(Asset).filter(Asset.id.in_(asset_ids)).all()
                    asset_data = [{"id": a.id, "path": a.path} for a in assets]

                    if not asset_data:
                        self.log.info("No assets found for deep analysis")
                        return

                    self.log.info(f"Starting deep AI analysis for {len(asset_data)} assets")

                    tag_runner = self.framework.get_service("tag_layer_runner")
                    if tag_runner:
                        # Run deep processing layers
                        tag_runner.run_layers_for_assets(asset_data, priority_filter=3)
                        self.events.publish("assets:deep_analysis_completed", asset_ids=asset_ids)
                        self.log.notification(f"Deep analysis completed for {len(asset_data)} assets")
                    else:
                        self.log.warning("Tag layer runner service not available")
                finally:
                    session.close()
            except Exception as e:
                self.log.error(f"Failed to run deep AI analysis: {e}", exc_info=True)

        worker = self.framework.get_service("worker_manager")
        worker.submit(deep_analysis_task)

    def _initial_scan(self, **kwargs):
        self.log.info("Performing initial asset scan...")
        output_dir_setting = self.settings.get("output_directory", "generated_media")
        output_dir = self.settings.resolve_user_path(output_dir_setting)
        self.scan_folder(output_dir)
        for folder in self.settings.get("library_folders", []):
            self.scan_folder(folder)

    def add_asset(self, path):
        if self.repository.get_by_path(path):
            return self.repository.get_by_path(path)

        file_hash = self._get_file_hash(path)
        if not file_hash:
            return None

        existing_by_hash = self.repository.get_by_id(file_hash)
        if existing_by_hash:
            self.log.info(
                f"Asset content already exists. Path: {path}, Hash: {file_hash}"
            )
            return existing_by_hash

        ext = os.path.splitext(path)[1].lower()
        asset_type = (
            AssetType.VIDEO if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"] else AssetType.IMAGE
        )
        thumb_path = self._create_thumbnail(path, file_hash)

        new_asset = Asset(
            id=file_hash, path=path, asset_type=asset_type, thumbnail_path=thumb_path
        )

        created_asset = self.repository.add(new_asset)
        if created_asset:
            # Announce that a new asset has been successfully added
            self.events.publish("assets:new_asset_added", asset_id=created_asset.id)

            # Auto-tag new asset with light AI processing
            self._schedule_auto_tagging(created_asset)

        return created_asset

    def _schedule_auto_tagging(self, asset):
        """Schedule automatic AI tagging for new assets"""
        def auto_tag_task():
            try:
                tag_runner = self.framework.get_service("tag_layer_runner")
                if tag_runner:
                    # Run only light/fast processing (priority 1) for immediate filtering
                    asset_data = [{"id": asset.id, "path": asset.path}]
                    tag_runner.run_layers_for_assets(asset_data, priority_filter=1)
                    self.events.publish("assets:tags_updated", asset_id=asset.id)
            except Exception as e:
                self.log.error(f"Failed to auto-tag asset {asset.id}: {e}", exc_info=True)

        worker = self.framework.get_service("worker_manager")
        worker.submit(auto_tag_task)

    def scan_folder(self, folder_path):
        abs_folder_path = folder_path
        if not os.path.isabs(abs_folder_path):
            abs_folder_path = self.settings.resolve_user_path(
                folder_path, ensure_exists=False
            )
        if not os.path.isdir(abs_folder_path):
            self.log.warning(f"Asset folder not found: {abs_folder_path}")
            return

        def scan_task():
            self.log.info(f"Scanning folder: {abs_folder_path}...")
            existing_paths = self.repository.get_existing_paths_in_folder(
                abs_folder_path
            )
            new_files_found = 0
            for root, _, files in os.walk(abs_folder_path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in self.SUPPORTED_TYPES:
                        full_path = os.path.join(root, file)
                        if full_path not in existing_paths:
                            self.add_asset(full_path)
                            new_files_found += 1
            if new_files_found > 0:
                self.events.publish("assets:database_updated")

        worker = self.framework.get_service("worker_manager")
        worker.submit(scan_task)

    def _get_file_hash(self, path):
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            return h.hexdigest()
        except (IOError, OSError) as e:
            self.log.error(f"Could not hash file {path}: {e}")
            return None

    def _create_thumbnail(self, path, file_hash):
        thumb_dir = self.settings.resolve_user_path("thumbnails")
        thumb_path = os.path.join(thumb_dir, f"{file_hash}.jpg")

        if os.path.exists(thumb_path):
            try:
                with Image.open(thumb_path) as cached_thumb:
                    if cached_thumb.size == self.THUMBNAIL_SIZE:
                        return thumb_path
            except Exception:
                self.log.warning(
                    f"Could not read cached thumbnail for {os.path.basename(path)}. Regenerating."
                )

        try:
            img = None
            if os.path.splitext(path)[1].lower() in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                cap.release()
            else:
                with Image.open(path) as opened_img:
                    img = opened_img.copy()

            if img:
                thumb = ImageOps.fit(img, self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                thumb.convert("RGB").save(thumb_path, "JPEG")
                return thumb_path
        except Exception as e:
            self.log.error(f"Failed to create thumbnail for {path}: {e}")
            return None
        return None
