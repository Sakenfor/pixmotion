
from __future__ import annotations
import json, os
from typing import Dict, List, Iterable, Optional

class TagIndexService:
    """Stores per-asset tags by layer without requiring a DB migration.
    Persists to ``user_data_root``/``tag_index.json``; structure:
    { asset_id: { layer_id: {"tags": [...], "meta": {...}} } }
    """
    def __init__(self, framework):
        self.framework = framework
        self.log = framework.log_manager
        self.settings = framework.get_service("settings_service")
        if self.settings:
            self._index_path = self.settings.resolve_user_path("tag_index.json")
        else:
            self._index_path = os.path.join(
                framework.get_project_root(), "data", "tag_index.json"
            )
            os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        self._index: Dict[str, Dict[str, Dict]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Dict]]:
        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self) -> None:
        try:
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            self.log.error("Failed saving tag index: %s", exc, exc_info=True)

    def get_layers_for_asset(self, asset_id: str) -> Dict[str, Dict]:
        return dict(self._index.get(asset_id, {}))

    def set_tags(self, asset_id: str, layer_id: str, tags: Iterable[str], meta: Optional[Dict]=None) -> None:
        entry = self._index.setdefault(asset_id, {})
        entry[layer_id] = { "tags": list({t.strip() for t in tags if t}), "meta": dict(meta or {}) }
        self._save()

    def add_tags(self, asset_id: str, layer_id: str, tags: Iterable[str]) -> None:
        entry = self._index.setdefault(asset_id, {})
        current = entry.setdefault(layer_id, {"tags": [], "meta": {}})
        s = set(current["tags"])
        for t in tags:
            if t:
                s.add(t.strip())
        current["tags"] = sorted(s)
        self._save()

    def query_assets(self, *, include_any: Dict[str, Iterable[str]]|None=None, include_all: Dict[str, Iterable[str]]|None=None, exclude: Dict[str, Iterable[str]]|None=None) -> List[str]:
        """Return asset_ids that match layered tag conditions.
        include_any: {layer: [tag,...]} -> matches if asset has ANY of tags in layer
        include_all: {layer: [tag,...]} -> matches if asset has ALL tags in layer
        exclude: {layer: [tag,...]} -> exclude if asset has ANY of these tags in layer
        """
        results = []
        for aid, layers in self._index.items():
            ok = True
            if include_any:
                for layer, tags in include_any.items():
                    if tags:
                        aset = set(map(str.lower, layers.get(layer, {}).get("tags", [])))
                        if not (aset & set(map(str.lower, tags))):
                            ok = False; break
                if not ok: continue
            if include_all:
                for layer, tags in include_all.items():
                    aset = set(map(str.lower, layers.get(layer, {}).get("tags", [])))
                    if not set(map(str.lower, tags)).issubset(aset):
                        ok = False; break
                if not ok: continue
            if exclude:
                for layer, tags in exclude.items():
                    aset = set(map(str.lower, layers.get(layer, {}).get("tags", [])))
                    if aset & set(map(str.lower, tags)):
                        ok = False; break
                if not ok: continue
            results.append(aid)
        return results

    def clear_layer(self, layer_id: str) -> None:
        for aid in list(self._index.keys()):
            self._index[aid].pop(layer_id, None)
            if not self._index[aid]:
                self._index.pop(aid, None)
        self._save()
