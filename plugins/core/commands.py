# D:/My Drive/code/pixmotion/plugins/core/commands.py
import os
import uuid
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from interfaces import ICommand
from .models import Asset


class ReloadPluginsCommand(ICommand):
    """
    Command to tear down and reload all plugins, services, and UI components.
    """

    def __init__(self, framework):
        self.framework = framework

    def execute(self, **kwargs):
        self.framework.reload_plugins()


class PasteFromClipboardCommand(ICommand):
    """
    Handles pasting from the clipboard, supporting raw images, Pinterest/web URLs,
    and local file paths. It creates a new asset and returns it.
    """

    def __init__(self, framework):
        self.log = framework.get_service("log_manager")
        self.settings = framework.get_service("settings_service")
        self.asset_service = framework.get_service("asset_service")
        self.importer_service = framework.get_service("web_importer_service")
        self.framework = framework

    def execute(self, **kwargs) -> Asset | None:
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        # --- Correctly check for content type in order: Image -> URL -> Text ---
        if mime_data.hasImage():
            self.log.info("Pasting image from clipboard...")
            q_image = clipboard.image()
            if q_image.isNull():
                self.log.error(
                    "Paste failed: Clipboard has image data, but it could not be read."
                )
                return None
            try:
                # --- FIX: Use the project root to build a reliable path ---
                output_dir = self.settings.resolve_user_path("clipboard")
                filename = f"paste_{uuid.uuid4().hex[:8]}.png"
                filepath = os.path.join(output_dir, filename)
                q_image.save(filepath, "PNG")
                self.log.info(f"Saved clipboard image to: {filepath}")
                return self.asset_service.add_asset(filepath)
            except Exception as e:
                self.log.error(
                    f"Failed to create asset from clipboard image: {e}", exc_info=True
                )
                return None

        elif mime_data.hasUrls():
            self.log.info("Pasting URL from clipboard...")
            url = mime_data.urls()[0].toString()
            if self.importer_service:
                local_path = self.importer_service.import_from_url(url)
                if local_path:
                    return self.asset_service.add_asset(local_path)

        elif mime_data.hasText():
            self.log.info("Pasting text from clipboard...")
            text = mime_data.text()
            if self.importer_service and ("http://" in text or "https://" in text):
                local_path = self.importer_service.import_from_url(text)
                if local_path:
                    return self.asset_service.add_asset(local_path)

        self.log.info(
            "Paste command ignored: No compatible content (Image, URL, Link-Text) found on clipboard."
        )
        return None


class ClearClipboardCommand(ICommand):
    """Command to clear all assets from the clipboard folder."""

    def __init__(self, framework):
        self.framework = framework

    def execute(self, **kwargs):
        asset_service = self.framework.get_service("asset_service")
        if asset_service:
            asset_service.clear_clipboard_assets()
