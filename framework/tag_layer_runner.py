from __future__ import annotations
import hashlib
import json
from typing import Any, Dict, Iterable, List
from framework.tag_layer_registry import TagLayerRegistry
from framework.ai_provider_manager import AIProviderManager
from plugins.tag_layers.tag_hierarchy_parser import TagHierarchyParser


class TagLayerRunner:
    def __init__(self, registry: TagLayerRegistry, ai_hub, framework=None):
        self.registry = registry
        self.ai_hub = ai_hub
        self.framework = framework
        self.ai_provider_manager = AIProviderManager(framework) if framework else None
        self.log = framework.get_service("log_manager") if framework else None

    def run_layer(self, layer_id: str, *, assets: Iterable[Dict[str, Any]]) -> None:
        layer_data = self.registry.get_layer(layer_id)
        if not layer_data or layer_data.get("stage") == "manual" or not layer_data.get("enabled", True):
            return

        # Get the best AI provider for this layer
        ai_provider = None
        if self.ai_provider_manager:
            ai_provider = self.ai_provider_manager.get_best_provider_for_layer(layer_data)
            if not ai_provider:
                if self.log:
                    self.log.warning(f"No enabled AI provider available for layer {layer_id}")
                return

        # Prepare engine configuration with custom prompt
        engine_config = layer_data.get("engine", {}).copy()
        custom_prompt = layer_data.get("prompt", "")
        if custom_prompt:
            engine_config["custom_prompt"] = custom_prompt

        # Add AI provider settings
        if ai_provider:
            engine_config["provider"] = ai_provider.id
            engine_config["provider_settings"] = ai_provider.settings
            model = ai_provider.settings.get("model") or engine_config.get("model")
        else:
            model = engine_config.get("model")

        if not model:
            return

        engine_hash = self._get_engine_hash(engine_config)
        assets_to_process = [{"id": a.get("id"), "path": a.get("path")} for a in assets if
                             a.get("id") and a.get("path")]
        if not assets_to_process:
            return

        # Log processing info
        if self.log:
            provider_name = ai_provider.name if ai_provider else "default"
            self.log.info(f"Processing {len(assets_to_process)} assets for layer '{layer_data.get('name', layer_id)}' using {provider_name}")

        batch_results = self.ai_hub.run_batch(model=model, assets=assets_to_process, config=engine_config)

        hierarchy_parser = TagHierarchyParser(layer_data.get("hierarchy", {}))

        for asset_result in batch_results:
            asset_id = asset_result.get("id")
            ai_output = asset_result.get("output")
            confidence = asset_result.get("confidence", 1.0)

            if not asset_id or not ai_output:
                continue

            values = self._map_result_to_values(layer_data, ai_output, confidence)
            final_values = {v['value'] for v in values if 'value' in v}

            # Apply hierarchy expansion
            for v in list(final_values):
                final_values.update(hierarchy_parser.get_ancestors(v))

            tags_to_add = [{'value': v, 'confidence': confidence, 'analysis_version': engine_hash} for v in final_values]
            if tags_to_add:
                self.registry.add_tags(asset_id=asset_id, layer_id=layer_id, values=tags_to_add, source="AI")

    def _get_engine_hash(self, engine_config: dict) -> str:
        config_str = json.dumps(engine_config, sort_keys=True)
        return hashlib.sha1(config_str.encode()).hexdigest()[:8]

    def _map_result_to_values(self, layer_data: dict, result: Any, default_confidence: float = 1.0) -> List[Dict[str, Any]]:
        vt = layer_data.get("value_type")
        if vt == "categorical":
            if isinstance(result, list):
                return [{"value": str(item.get("value", item)), "confidence": float(item.get("confidence", default_confidence))} for
                        item in result if isinstance(item, dict) or isinstance(item, str)]
            if isinstance(result, dict):
                if "labels" in result and isinstance(result["labels"], list):
                    return [{"value": str(v.get("value", v)), "confidence": float(v.get("confidence", default_confidence))} for v in
                            result["labels"]]
                if "top" in result:
                    return [{"value": str(result["top"]), "confidence": float(result.get("confidence", default_confidence))}]
            if isinstance(result, str):
                return [{"value": result, "confidence": default_confidence}]
        elif vt == "numeric":
            if isinstance(result, (int, float)):
                return [{"numeric_value": float(result), "confidence": default_confidence}]
            if isinstance(result, dict) and "value" in result:
                return [{"numeric_value": float(result["value"]), "confidence": float(result.get("confidence", default_confidence))}]
        elif vt == "text":
            if isinstance(result, str):
                return [{"text_value": result, "confidence": default_confidence}]
            if isinstance(result, dict) and "text" in result:
                return [{"text_value": str(result["text"]), "confidence": float(result.get("confidence", default_confidence))}]
        return []

    def run_layers_for_assets(self, assets: Iterable[Dict[str, Any]], priority_filter: int = None) -> None:
        """Run all enabled layers for given assets, optionally filtered by processing priority"""
        layers = self.registry.list_layers()
        enabled_layers = [l for l in layers if l.get("enabled", True) and l.get("stage") != "manual"]

        if priority_filter is not None:
            enabled_layers = [l for l in enabled_layers if l.get("processing_priority", 1) == priority_filter]

        # Sort by priority (light processing first)
        enabled_layers.sort(key=lambda x: x.get("processing_priority", 1))

        for layer in enabled_layers:
            self.run_layer(layer["id"], assets=assets)
