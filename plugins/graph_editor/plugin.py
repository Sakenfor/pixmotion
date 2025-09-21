"""Graph editor plugin entry."""
from __future__ import annotations

from typing import Any

from interfaces import IPlugin

from .panel import GraphExplorerPanel  # Canonical dock implementation


class Plugin(IPlugin):
    def register(self, framework):
        framework.register_contribution(
            "ui_docks",
            {
                "id": "graph_explorer",
                "class": GraphExplorerPanel,
                "title": "Graph Explorer",
                "default_area": "right",
            },
        )


def register_plugin(service_registry: Any) -> None:
    framework = getattr(service_registry, "get", lambda *_: None)("framework")
    if framework is None:
        raise RuntimeError("Framework service not registered in ServiceRegistry.")
    Plugin().register(framework)
