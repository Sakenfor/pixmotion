# story_studio_project/plugins/generation/plugin.py
from interfaces import IPlugin
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
            "services",
            {"id": "pixverse_service", "instance": pixverse_service}
        )

        # Register Commands
        framework.register_contribution(
            "commands",
            {"id": "story.generate_video", "class": GenerateVideoCommand}
        )

        # Register a single, consolidated UI Dock
        framework.register_contribution(
            "ui_docks",
            {
                "id": "generator_panel",
                "class": GeneratorPanel,
                "title": "Generator",
                "default_area": "right"
            }
        )

