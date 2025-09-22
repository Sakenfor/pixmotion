from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.tag_layers.scan_profile_service import ScanProfileService


class _StubLog:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class _RecordingTagIndex:
    def __init__(self):
        self.records: dict[str, dict[str, set[str]]] = {}

    def add_tags(self, asset_id: str, layer_id: str, tags):
        asset_layers = self.records.setdefault(asset_id, {})
        layer_tags = asset_layers.setdefault(layer_id, set())
        for tag in tags:
            if tag:
                layer_tags.add(tag)


class _StubRegistry:
    def __init__(self):
        self._layers: dict[str, dict[str, object]] = {}

    def register_layer(self, layer_id: str, descriptor: dict[str, object]):
        entry = dict(descriptor)
        entry.setdefault("id", layer_id)
        self._layers[layer_id] = entry

    def get_layer(self, layer_id: str) -> dict[str, object] | None:
        return self._layers.get(layer_id)


class _StubRepository:
    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def get_path_by_id(self, asset_id: str) -> str | None:
        return self._mapping.get(asset_id)


class _StubSettings:
    def __init__(self, base_dir: Path):
        self._base_dir = base_dir

    def resolve_user_path(self, filename: str) -> str:
        path = self._base_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)


class _StubFramework:
    def __init__(self, services: dict[str, object], project_root: Path):
        self._services = services
        self._project_root = project_root
        self.log_manager = services.get("log_manager")

    def get_service(self, service_id: str):
        return self._services.get(service_id)

    def get_project_root(self) -> Path:
        return self._project_root


class ScanProfileServiceTests(unittest.TestCase):
    def test_quick_profile_populates_distinct_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            log = _StubLog()
            registry = _StubRegistry()
            registry.register_layer(
                "basic",
                {"name": "Basic File Tags", "generator": "services.tag_layers.ai_quick_generator:AIQuickGenerator"},
            )
            registry.register_layer(
                "ai_quick",
                {"name": "AI Quick", "generator": "services.tag_layers.ai_quick_generator:AIQuickGenerator"},
            )
            tag_index = _RecordingTagIndex()
            repository = _StubRepository({"asset-001": str(base / "Portrait_Dog.jpg")})
            settings = _StubSettings(base)
            services = {
                "log_manager": log,
                "tag_layer_registry": registry,
                "tag_index_service": tag_index,
                "asset_repository": repository,
                "settings_service": settings,
            }
            framework = _StubFramework(services, base)

            service = ScanProfileService(framework)
            processed = service.run_profile("quick_pass", asset_ids=["asset-001"])

            self.assertEqual(processed, 2)
            layers = tag_index.records.get("asset-001")
            self.assertIsNotNone(layers)
            self.assertIn("basic", layers)
            self.assertIn("ai_quick", layers)
            self.assertEqual(len(layers), 2)
            self.assertIn("portrait", layers["basic"])
            self.assertIn("portrait", layers["ai_quick"])


if __name__ == "__main__":  # pragma: no cover - unittest boilerplate
    unittest.main()
