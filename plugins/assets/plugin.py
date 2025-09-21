# story_studio_project/plugins/assets/plugin.py
from interfaces import IPlugin
from typing import Any

from .commands import ScanFolderCommand, RescanEmotionPackagesCommand
from .models import (
    Asset,
    AssetType,
    EmotionClip,
)
from .repositories import AssetRepository, EmotionClipRepository
from .services import (
    AssetService,
    EmotionLoopSelector,
    EmotionPackageService,
    ThumbnailService,
)
from .ui import AssetBrowserPanel
# Import models to ensure they are seen by SQLAlchemy


class Plugin(IPlugin):
    """Registers asset management services, UI, and commands."""

    def register(self, framework):
        # The Asset models are now defined here, but they use the core's Base.
        # This contribution makes the framework aware of them.
        framework.register_contribution(
            "database_models", {"classes": [Asset, AssetType, EmotionClip]}
        )

        # 1. Create the repository first
        asset_repository = AssetRepository(framework)
        emotion_repository = EmotionClipRepository(framework)

        # 2. Create the service and give it the repository
        asset_service = AssetService(framework, asset_repository)
        framework.register_contribution(
            "services", {"id": "asset_service", "instance": asset_service}
        )

        emotion_service = EmotionPackageService(framework, asset_service, emotion_repository)
        framework.register_contribution(
            "services",
            {"id": "emotion_package_service", "instance": emotion_service},
        )

        emotion_selector = EmotionLoopSelector(framework, emotion_repository, asset_service)
        framework.register_contribution(
            "services",
            {"id": "emotion_loop_selector", "instance": emotion_selector},
        )
        emotion_service.register_selector(emotion_selector)

        thumbnail_service = ThumbnailService(framework)
        framework.register_contribution(
            "services", {"id": "thumbnail_service", "instance": thumbnail_service}
        )

        # 3. Register commands
        framework.register_contribution(
            "commands", {"id": "assets.scan_folder", "class": ScanFolderCommand}
        )
        framework.register_contribution(
            "commands",
            {
                "id": "assets.resync_emotion_packages",
                "class": RescanEmotionPackagesCommand,
            },
        )

        # 4. Register UI panels
        framework.register_contribution(
            "ui_docks",
            {
                "id": "asset_browser",
                "class": AssetBrowserPanel,
                "title": "Asset Browser",
                "default_area": "left",
            },
        )


def register_plugin(service_registry: Any) -> None:
    """Entry point declared in the plugin manifest."""
    framework = getattr(service_registry, "get", lambda *_: None)("framework")
    if framework is None:
        raise RuntimeError("Framework service not registered in ServiceRegistry.")
    Plugin().register(framework)


