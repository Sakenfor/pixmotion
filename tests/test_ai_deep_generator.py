from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.tag_layers.ai_deep_generator import AIDeepGenerator


class _StubLog:
    def __init__(self):
        self.errors: list[tuple[str, tuple[object, ...]]] = []

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, message: str, *args, **kwargs):
        self.errors.append((message, args))


class _RecordingTagIndex:
    def __init__(self, initial: dict[str, dict[str, dict]] | None = None):
        self.layers = initial or {}

    def get_layers_for_asset(self, asset_id: str) -> dict[str, dict]:
        return dict(self.layers.get(asset_id, {}))

    def set_tags(self, asset_id: str, layer_id: str, tags, meta=None):
        asset_layers = self.layers.setdefault(asset_id, {})
        asset_layers[layer_id] = {
            "tags": sorted({str(tag) for tag in tags}),
            "meta": dict(meta or {}),
        }


class _StubRepository:
    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def get_path_by_id(self, asset_id: str) -> str | None:
        return self._mapping.get(asset_id)


class _StubFramework:
    def __init__(self, services: dict[str, object], project_root: Path):
        self._services = services
        self._project_root = project_root
        self.log_manager = services.get("log_manager")

    def get_service(self, service_id: str):
        return self._services.get(service_id)

    def get_project_root(self) -> Path:
        return self._project_root


class AIDeepGeneratorTests(unittest.TestCase):
    def test_process_asset_emits_curated_tags_and_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            asset_path = Path(tmp) / "warm_portrait.png"
            with Image.new("RGB", (32, 32), (255, 210, 140)) as img:
                img.save(asset_path)

            log = _StubLog()
            tag_index = _RecordingTagIndex(
                {
                    "asset-warm": {
                        "ai_quick": {"tags": ["Portrait"]},
                    }
                }
            )
            repository = _StubRepository({"asset-warm": str(asset_path)})
            services = {
                "log_manager": log,
                "tag_index_service": tag_index,
                "asset_repository": repository,
            }
            framework = _StubFramework(services, ROOT)
            generator = AIDeepGenerator(framework, {"id": "ai_deep"})

            generator.process_asset("asset-warm")

            record = tag_index.layers["asset-warm"]["ai_deep"]
            tags = set(record["tags"])
            self.assertIn("emotion:joyful", tags)
            self.assertIn("subject:person", tags)
            self.assertIn("palette:warm", tags)
            self.assertNotIn("needs_review", tags)

            meta = record["meta"]
            self.assertGreater(meta["confidence"], 0.34)
            self.assertIn("emotion:joyful", meta["distribution"])
            self.assertAlmostEqual(sum(meta["distribution"].values()), 1.0, places=3)
            self.assertIn("brightness", meta["features"])

    def test_missing_path_marks_needs_review(self) -> None:
        log = _StubLog()
        tag_index = _RecordingTagIndex()
        repository = _StubRepository({})
        services = {
            "log_manager": log,
            "tag_index_service": tag_index,
            "asset_repository": repository,
        }
        framework = _StubFramework(services, ROOT)
        generator = AIDeepGenerator(framework, {"id": "ai_deep"})

        generator.process_asset("asset-missing")

        record = tag_index.layers["asset-missing"]["ai_deep"]
        self.assertEqual(set(record["tags"]), {"needs_review"})
        self.assertIn("error", record["meta"])


if __name__ == "__main__":  # pragma: no cover - unittest boilerplate
    unittest.main()
