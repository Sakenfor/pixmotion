# plugins/tag_layers/plugin.py
from interfaces import IPlugin
from typing import Any
from framework.tag_layer_registry import TagLayerRegistry
from framework.tag_layer_runner import TagLayerRunner
from .tag_layer_editor import TagLayerEditorPanel  # MODIFIED: Import the new UI panel


class Plugin(IPlugin):
    def register(self, framework):
        # Register the backend services (this part is correct)
        registry = TagLayerRegistry(framework)
        framework.register_contribution("services", {"id": "tag_layer_registry", "instance": registry})

        ai_hub = framework.get_service("ai_hub") or _NullAIHub()
        runner = TagLayerRunner(registry=registry, ai_hub=ai_hub, framework=framework)
        framework.register_contribution("services", {"id": "tag_layer_runner", "instance": runner})

        # MODIFIED: Register the editor panel as a dockable UI widget
        framework.register_contribution(
            "ui_docks",
            {
                "id": "tag_layer_editor",
                "class": TagLayerEditorPanel,
                "title": "Tag Layer Editor",
                "default_area": "right",
            },
        )

        # Default layers will be created by the framework after database initialization


class _NullAIHub:
    """Graceful no-op AI Hub so the plugin doesn't crash without the service."""

    def run(self, model: str, asset: Any, **kwargs):
        return []

    def run_batch(self, model: str, assets: list[dict[str, Any]], **kwargs) -> list[dict[str, Any]]:
        print(f"AI Hub received batch request for model '{model}' on {len(assets)} assets.")
        return []


def register_plugin(service_registry: Any) -> None:
    """Entry point declared in the plugin manifest."""
    framework = getattr(service_registry, "get", lambda *_: None)("framework")
    if framework is None:
        raise RuntimeError("Framework service not registered in ServiceRegistry.")
    Plugin().register(framework)


