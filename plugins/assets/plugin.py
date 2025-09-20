# story_studio_project/plugins/assets/plugin.py
from interfaces import IPlugin
from .services import AssetService
from .repository import AssetRepository
from .commands import ScanFolderCommand
from .browser import AssetBrowserPanel
from .thumbnail_service import ThumbnailService
from .models import Asset, AssetType  # Import models to ensure they are seen by SQLAlchemy


class Plugin(IPlugin):
    """Registers asset management services, UI, and commands."""

    def register(self, framework):
        # The Asset models are now defined here, but they use the core's Base.
        # This contribution makes the framework aware of them.
        framework.register_contribution(
            "database_models",
            {"classes": [Asset, AssetType]}
        )

        # 1. Create the repository first
        asset_repository = AssetRepository(framework)

        # 2. Create the service and give it the repository
        asset_service = AssetService(framework, asset_repository)
        framework.register_contribution(
            "services",
            {"id": "asset_service", "instance": asset_service}
        )

        thumbnail_service = ThumbnailService(framework)
        framework.register_contribution("services", {"id": "thumbnail_service", "instance": thumbnail_service})

        # 3. Register commands
        framework.register_contribution(
            "commands",
            {"id": "assets.scan_folder", "class": ScanFolderCommand}
        )

        # 4. Register UI panels
        framework.register_contribution(
            "ui_docks",
            {
                "id": "asset_browser",
                "class": AssetBrowserPanel,
                "title": "Asset Browser",
                "default_area": "left"
            }
        )
