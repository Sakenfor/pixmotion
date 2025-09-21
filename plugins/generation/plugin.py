# story_studio_project/plugins/generation/plugin.py
from interfaces import IPlugin
from typing import Any
from .services import PixverseService
from .commands import GenerateVideoCommand
from .panels import GeneratorPanel


class Plugin(IPlugin):
    """
    This plugin provides all functionality related to video generation.
    """

    def register(self, framework):
        # Register Services
        pixverse_service = PixverseService(framework)
        framework.register_contribution(
            "services", {"id": "pixverse_service", "instance": pixverse_service}
        )

        # Register Commands
        framework.register_contribution(
            "commands", {"id": "story.generate_video", "class": GenerateVideoCommand}
        )

        # Register a single, consolidated UI Dock
        framework.register_contribution(
            "ui_docks",
            {
                "id": "generator_panel",
                "class": GeneratorPanel,
                "title": "Generator",
                "default_area": "right",
            },
        )


def register_plugin(service_registry: Any) -> None:
    """Entry point declared in the plugin manifest."""
    framework = getattr(service_registry, "get", lambda *_: None)("framework")
    if framework is None:
        raise RuntimeError("Framework service not registered in ServiceRegistry.")
    Plugin().register(framework)
