"""
Prompt Enhancer Plugin for PixMotion

This plugin enhances video generation prompts using AI Hub models.
It integrates with the existing Pixverse Generator Panel to provide
seamless prompt enhancement functionality.
"""
from interfaces import IPlugin
from typing import Any
from .services import PromptEnhancerService
from .extension import GeneratorPanelExtension


class Plugin(IPlugin):
    """
    Prompt Enhancer Plugin - Enhances prompts for video generation using AI Hub models
    """

    def register(self, framework):
        """Register the plugin services and UI extensions"""

        # Register the prompt enhancer service
        enhancer_service = PromptEnhancerService(framework)
        framework.register_contribution(
            "services",
            {
                "id": "prompt_enhancer_service",
                "instance": enhancer_service
            }
        )

        # Register the UI extension that modifies the existing Generator Panel
        panel_extension = GeneratorPanelExtension(framework)
        framework.register_contribution(
            "ui_extensions",
            {
                "id": "generator_panel_prompt_enhancer",
                "instance": panel_extension,
                "target": "generator_panel",
                "type": "enhancement"
            }
        )


def register_plugin(service_registry: Any) -> None:
    """Entry point declared in the plugin manifest."""
    framework = getattr(service_registry, "get", lambda *_: None)("framework")
    if framework is None:
        raise RuntimeError("Framework service not registered in ServiceRegistry.")
    Plugin().register(framework)