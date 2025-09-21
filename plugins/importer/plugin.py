# D:/My Drive/code/pixmotion/plugins/importer/plugin.py
from interfaces import IPlugin
from typing import Any
from .services import WebImporterService


class Plugin(IPlugin):
    def register(self, framework):
        importer_service = WebImporterService(framework)
        framework.register_contribution(
            "services", {"id": "web_importer_service", "instance": importer_service}
        )


def register_plugin(service_registry: Any) -> None:
    """Entry point declared in the plugin manifest."""
    framework = getattr(service_registry, "get", lambda *_: None)("framework")
    if framework is None:
        raise RuntimeError("Framework service not registered in ServiceRegistry.")
    Plugin().register(framework)
