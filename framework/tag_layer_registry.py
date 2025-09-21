
from __future__ import annotations
from typing import Any, Dict, Optional

class TagLayerRegistry:
    """Registry for modular tag layers contributed by plugins or settings."""
    def __init__(self, log_manager):
        self.log = log_manager
        self._layers: Dict[str, Dict[str, Any]] = {}

    def register_layer(self, layer_id: str, descriptor: Dict[str, Any], *, plugin_uuid: str | None = None) -> None:
        if not layer_id:
            self.log.error("Cannot register tag layer without id.")
            return
        entry = dict(descriptor)
        entry.setdefault("id", layer_id)
        if plugin_uuid:
            entry.setdefault("plugin_uuid", plugin_uuid)
        self._layers[layer_id] = entry
        self.log.info("Registered tag layer '%s'%s", layer_id, f" from {plugin_uuid}" if plugin_uuid else "")

    def list_layers(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._layers)

    def get_layer(self, layer_id: str) -> Optional[Dict[str, Any]]:
        return self._layers.get(layer_id)

    def clear_by_plugin(self, plugin_uuid: str) -> None:
        to_remove = [k for k,v in self._layers.items() if v.get("plugin_uuid")==plugin_uuid]
        for k in to_remove:
            self._layers.pop(k, None)

    def clear(self) -> None:
        self._layers.clear()
