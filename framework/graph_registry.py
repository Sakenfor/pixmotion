from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional


class GraphRegistry:
    """Holds node/edge type descriptors and related graph metadata."""

    def __init__(self, log_manager):
        self.log = log_manager
        self._node_types: Dict[str, Dict[str, Any]] = {}
        self._relation_types: Dict[str, Dict[str, Any]] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._validators: List[Dict[str, Any]] = []
        self._runtime_handlers: Dict[str, Dict[str, Any]] = {}
        self._personas: Dict[str, Dict[str, Any]] = {}
        self._action_bundles: Dict[str, Dict[str, Any]] = {}
        self._qualitative_scales: Dict[str, Dict[str, Any]] = {}

        self._plugin_index: Dict[str, Dict[str, set[str]]] = {
            "node_types": defaultdict(set),
            "relation_types": defaultdict(set),
            "templates": defaultdict(set),
            "runtime_handlers": defaultdict(set),
            "personas": defaultdict(set),
            "action_bundles": defaultdict(set),
            "qualitative_scales": defaultdict(set),
        }
        self._validator_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # --- Registration -------------------------------------------------

    def register_node_type(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        node_type = descriptor.get("id")
        if not node_type:
            self.log.error("Graph node type registration missing 'id'.")
            return
        self._node_types[node_type] = dict(descriptor)
        self._plugin_index["node_types"][plugin_uuid].add(node_type)
        self.log.info("Registered graph node type '%s'", node_type)

    def register_relation_type(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        relation_type = descriptor.get("id")
        if not relation_type:
            self.log.error("Graph relation type registration missing 'id'.")
            return
        self._relation_types[relation_type] = dict(descriptor)
        self._plugin_index["relation_types"][plugin_uuid].add(relation_type)
        self.log.info("Registered graph relation type '%s'", relation_type)

    def register_template(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        template_id = descriptor.get("id")
        if not template_id:
            self.log.error("Graph template registration missing 'id'.")
            return
        self._templates[template_id] = dict(descriptor)
        self._plugin_index["templates"][plugin_uuid].add(template_id)
        self.log.info("Registered graph template '%s'", template_id)

    def register_validator(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        payload = dict(descriptor)
        payload.setdefault("plugin_uuid", plugin_uuid)
        self._validators.append(payload)
        self._validator_index[plugin_uuid].append(payload)
        self.log.info("Registered graph validator from plugin %s", plugin_uuid)

    def register_runtime_handler(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        handler_id = descriptor.get("id")
        if not handler_id:
            self.log.error("Graph runtime handler registration missing 'id'.")
            return
        self._runtime_handlers[handler_id] = dict(descriptor)
        self._plugin_index["runtime_handlers"][plugin_uuid].add(handler_id)
        self.log.info("Registered graph runtime handler '%s'", handler_id)

    def register_persona(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        persona_id = descriptor.get("id")
        if not persona_id:
            self.log.error("Graph persona registration missing 'id'.")
            return
        self._personas[persona_id] = dict(descriptor)
        self._plugin_index["personas"][plugin_uuid].add(persona_id)
        self.log.info("Registered orchestrator persona '%s'", persona_id)

    def register_action_bundle(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        bundle_id = descriptor.get("id")
        if not bundle_id:
            self.log.error("Graph action bundle registration missing 'id'.")
            return
        self._action_bundles[bundle_id] = dict(descriptor)
        self._plugin_index["action_bundles"][plugin_uuid].add(bundle_id)
        self.log.info("Registered graph action bundle '%s'", bundle_id)

    def register_qualitative_scale(self, descriptor: Dict[str, Any], *, plugin_uuid: str) -> None:
        scale_id = descriptor.get("id")
        if not scale_id:
            self.log.error("Graph qualitative scale registration missing 'id'.")
            return
        self._qualitative_scales[scale_id] = dict(descriptor)
        self._plugin_index["qualitative_scales"][plugin_uuid].add(scale_id)
        self.log.info("Registered qualitative scale '%s'", scale_id)

    # --- Accessors ----------------------------------------------------

    @property
    def node_types(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._node_types)

    @property
    def relation_types(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._relation_types)

    @property
    def templates(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._templates)

    @property
    def validators(self) -> List[Dict[str, Any]]:
        return list(self._validators)

    @property
    def runtime_handlers(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._runtime_handlers)

    @property
    def personas(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._personas)

    @property
    def action_bundles(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._action_bundles)

    @property
    def qualitative_scales(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._qualitative_scales)

    def get_node_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        return self._node_types.get(type_id)

    def get_relation_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        return self._relation_types.get(type_id)

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return self._templates.get(template_id)

    def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        return self._personas.get(persona_id)

    def get_action_bundle(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        return self._action_bundles.get(bundle_id)

    def get_qualitative_scale(self, scale_id: str) -> Optional[Dict[str, Any]]:
        return self._qualitative_scales.get(scale_id)

    # --- Clearing -----------------------------------------------------

    def clear_by_plugin(self, plugin_uuid: str) -> None:
        for category, index in self._plugin_index.items():
            keys = index.pop(plugin_uuid, set())
            storage = getattr(self, f"_{category}")
            for key in keys:
                storage.pop(key, None)

        validators = self._validator_index.pop(plugin_uuid, [])
        for validator in validators:
            try:
                self._validators.remove(validator)
            except ValueError:
                pass

    def clear(self) -> None:
        self._node_types.clear()
        self._relation_types.clear()
        self._templates.clear()
        self._validators.clear()
        self._runtime_handlers.clear()
        self._personas.clear()
        self._action_bundles.clear()
        self._qualitative_scales.clear()
        for index in self._plugin_index.values():
            index.clear()
        self._validator_index.clear()
