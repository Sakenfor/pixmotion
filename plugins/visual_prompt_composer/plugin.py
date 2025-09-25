"""
Visual Prompt Composer Plugin

Main plugin registration and initialization for the Visual Prompt Composer.
"""

from interfaces import IPlugin
from .services.composer_service import VisualComposerService
from .ui.composer_panel import VisualPromptComposerPanel
from .commands import (
    NewSceneCommand,
    SaveSceneCommand,
    LoadSceneCommand,
    GeneratePromptCommand,
    ExportToGeneratorCommand,
)


class VisualPromptComposerPlugin(IPlugin):
    """Visual Prompt Composer plugin implementation"""

    def register(self, framework):
        """Register plugin services and UI components"""
        log = framework.get_service("log_manager")
        log.info("Registering Visual Prompt Composer plugin...")

        try:
            # Register core composer service
            composer_service = VisualComposerService(framework)
            composer_service.initialize()  # Explicitly initialize
            framework.register_contribution("services", {
                "id": "visual_composer_service",
                "instance": composer_service
            })

            # Register spatial intelligence engine as a service
            from .services.spatial_engine import SpatialIntelligenceEngine
            spatial_engine = SpatialIntelligenceEngine(framework)
            spatial_engine.initialize()  # Explicitly initialize
            framework.register_contribution("services", {
                "id": "spatial_intelligence_service",
                "instance": spatial_engine
            })

            # Link the services together
            composer_service.set_spatial_engine(spatial_engine)

            # Register main UI panel as a dock widget
            framework.register_contribution("ui_docks", {
                "id": "visual_prompt_composer",
                "class": VisualPromptComposerPanel,
                "title": "🎬 Visual Prompt Composer",
                "default_area": "right",
                "default_visible": True
            })

            # Register commands
            self._register_commands(framework)

            log.info("Visual Prompt Composer plugin registered successfully")

        except Exception as e:
            log.error(f"Failed to register Visual Prompt Composer plugin: {e}")
            raise

    def _register_commands(self, framework):
        """Register plugin commands"""
        # Register all commands
        framework.register_contribution("commands", {
            "id": "composer.new_scene",
            "class": NewSceneCommand,
            "description": "Create a new visual scene"
        })
        framework.register_contribution("commands", {
            "id": "composer.save_scene",
            "class": SaveSceneCommand,
            "description": "Save the current scene to file"
        })
        framework.register_contribution("commands", {
            "id": "composer.load_scene",
            "class": LoadSceneCommand,
            "description": "Load a scene from file"
        })
        framework.register_contribution("commands", {
            "id": "composer.generate_prompt",
            "class": GeneratePromptCommand,
            "description": "Generate AI prompt from current scene"
        })
        framework.register_contribution("commands", {
            "id": "composer.export_to_generator",
            "class": ExportToGeneratorCommand,
            "description": "Export generated prompt to video generator"
        })


def register_plugin(service_registry):
    """Entry point for plugin registration"""
    framework = service_registry.get("framework")
    plugin = VisualPromptComposerPlugin()
    plugin.register(framework)