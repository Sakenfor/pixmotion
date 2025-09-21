from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


class TemplateRegistry:
    """Stores template metadata contributed by plugins for reuse across scenarios."""

    def __init__(self, log_manager):
        self.log = log_manager
        self._templates: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._plugin_index: Dict[str, set[tuple[str, str]]] = {}

    def register_template(
        self,
        template_type: str,
        template_id: str,
        payload: Dict[str, Any],
        *,
        plugin_uuid: str,
    ) -> None:
        """Registers a single template definition.

        Parameters
        ----------
        template_type:
            Logical category for the template (e.g. ``"npc_profile"``).
        template_id:
            Unique identifier within ``template_type``.
        payload:
            Arbitrary template metadata supplied by the contributing plugin.
        plugin_uuid:
            UUID of the plugin that owns this template. Used for cleanup on unload.
        """

        template_type = template_type.strip().lower()
        template_id = template_id.strip()
        if not template_type or not template_id:
            self.log.warning(
                "Ignoring template registration with missing type or id: %s / %s",
                template_type,
                template_id,
            )
            return

        template_bucket = self._templates.setdefault(template_type, {})
        template_bucket[template_id] = {
            "data": payload,
            "plugin_uuid": plugin_uuid,
        }

        self._plugin_index.setdefault(plugin_uuid, set()).add((template_type, template_id))
        self.log.debug(
            "Registered template '%s' under type '%s' from plugin %s",
            template_id,
            template_type,
            plugin_uuid,
        )

    def register_bundle(
        self,
        template_type: str,
        entries: Iterable[Dict[str, Any]],
        *,
        plugin_uuid: str,
    ) -> None:
        """Registers multiple template entries of the same type."""

        for entry in entries:
            if not isinstance(entry, dict):
                self.log.warning(
                    "Template bundle entry for type '%s' is not a dict: %s",
                    template_type,
                    entry,
                )
                continue

            template_id = str(entry.get("id", "")).strip()
            payload = entry.get("data") if isinstance(entry.get("data"), dict) else {
                k: v for k, v in entry.items() if k != "id"
            }
            if not template_id:
                self.log.warning(
                    "Skipping template bundle entry without id for type '%s'",
                    template_type,
                )
                continue

            self.register_template(
                template_type,
                template_id,
                payload,
                plugin_uuid=plugin_uuid,
            )

    def get_template(self, template_type: str, template_id: str) -> Optional[Dict[str, Any]]:
        """Returns the payload for a stored template, if present."""

        template_type = template_type.strip().lower()
        template_id = template_id.strip()
        bucket = self._templates.get(template_type, {})
        entry = bucket.get(template_id)
        if not entry:
            return None
        return entry["data"]

    def list_templates(self, template_type: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Returns all templates, optionally filtered by type."""

        if template_type is None:
            return {
                key: {tpl_id: data["data"] for tpl_id, data in templates.items()}
                for key, templates in self._templates.items()
            }

        template_type = template_type.strip().lower()
        bucket = self._templates.get(template_type, {})
        return {tpl_id: data["data"] for tpl_id, data in bucket.items()}

    def clear_by_plugin(self, plugin_uuid: str) -> None:
        """Removes all templates registered by the specified plugin."""

        registrations = self._plugin_index.pop(plugin_uuid, set())
        for template_type, template_id in registrations:
            bucket = self._templates.get(template_type)
            if not bucket:
                continue
            bucket.pop(template_id, None)
            if not bucket:
                self._templates.pop(template_type, None)

    def clear(self) -> None:
        """Removes all registered templates."""

        self._templates.clear()
        self._plugin_index.clear()
