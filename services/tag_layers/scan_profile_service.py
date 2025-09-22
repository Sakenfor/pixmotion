
from __future__ import annotations
import json, os
from typing import Dict, Iterable, Optional
from importlib import import_module


DEFAULT_PROFILES: Dict[str, Dict] = {
    "quick_pass": {
        "label": "Quick Sort Pass",
        "layers": ["basic", "ai_quick"],
        "filter": {"asset_type": ["image", "video"]},
    },
    "deep_pass": {
        "label": "Deep AI Pass",
        "layers": ["ai_deep"],
        "filter": {"include_layers_any": {"ai_quick": ["portrait", "animal"]}},
    },
}


LEGACY_QUICK_TAGS = {"person_detected", "portrait"}


def _resolve_callable(path: str):
    module, sep, attr = path.partition(":")
    if not sep:
        module, attr = path.rsplit(".", 1)
    mod = import_module(module)
    return getattr(mod, attr)

class ScanProfileService:
    """Runs configurable scan profiles that invoke layer generators on filtered assets."""
    def __init__(self, framework):
        self.framework = framework
        self.log = framework.log_manager
        self.registry = framework.get_service("tag_layer_registry")
        self.tag_index = framework.get_service("tag_index_service")
        self.asset_repo = framework.get_service("asset_repository")  # optional
        self.settings = framework.get_service("settings_service")
        if self.settings:
            self._profiles_path = self.settings.resolve_user_path("scan_profiles.json")
        else:
            self._profiles_path = os.path.join(
                framework.get_project_root(), "data", "scan_profiles.json"
            )
            os.makedirs(os.path.dirname(self._profiles_path), exist_ok=True)
        self._ensure_profiles_file()

    def _ensure_profiles_file(self) -> None:
        if not os.path.exists(self._profiles_path):
            self._write_default_profiles(); return
        try:
            with open(self._profiles_path, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            self._write_default_profiles(); return
        deep_filter = (
            (current.get("deep_pass") or {})
            .get("filter", {})
            .get("include_layers_any", {})
            .get("ai_quick", [])
        )
        tags = {t.lower() for t in deep_filter if t}
        if tags == {t.lower() for t in LEGACY_QUICK_TAGS}:
            if self.log:
                self.log.info("Updating scan_profiles.json to latest defaults")
            self._write_default_profiles()

    def _write_default_profiles(self):
        os.makedirs(os.path.dirname(self._profiles_path), exist_ok=True)
        with open(self._profiles_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PROFILES, f, indent=2)

    def list_profiles(self) -> Dict[str, Dict]:
        try:
            with open(self._profiles_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def run_profile(self, profile_id: str, *, asset_ids: Optional[Iterable[str]] = None) -> int:
        profiles = self.list_profiles()
        spec = profiles.get(profile_id)
        if not spec:
            self.log.error("Unknown scan profile '%s'", profile_id); return 0
        layer_ids = spec.get("layers") or []
        # Resolve asset_ids by filter if not explicitly provided
        targets = set(asset_ids or [])
        if not targets:
            targets = self._resolve_targets_by_filter(spec.get("filter", {}))
        count = 0
        for layer_id in layer_ids:
            layer_desc = self.registry.get_layer(layer_id)
            if not layer_desc:
                self.log.warning("Layer '%s' not registered; skipping.", layer_id); continue
            generator_path = layer_desc.get("generator")
            if not generator_path:
                self.log.warning("Layer '%s' missing generator; skipping.", layer_id); continue
            try:
                runner = _resolve_callable(generator_path)(self.framework, layer_desc)
            except Exception as exc:
                self.log.error("Failed to instantiate generator for '%s': %s", layer_id, exc, exc_info=True)
                continue
            for aid in targets:
                try:
                    runner.process_asset(aid)
                    count += 1
                except Exception as exc:
                    self.log.error("Generator error on asset %s for layer %s: %s", aid, layer_id, exc, exc_info=True)
        return count

    def _resolve_targets_by_filter(self, rule: Dict) -> set[str]:
        # Simple filter: by layered tags using TagIndexService; DB type filters optional
        include_any = rule.get("include_layers_any") or {}
        include_all = rule.get("include_layers_all") or {}
        exclude = rule.get("exclude_layers") or {}
        ids = set(self.tag_index.query_assets(include_any=include_any, include_all=include_all, exclude=exclude))
        # TODO: asset_type filter via repository if available
        return ids
