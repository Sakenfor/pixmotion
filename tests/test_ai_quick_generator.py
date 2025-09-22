from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.tag_layers.ai_quick_generator import AIQuickGenerator


class _StubLog:
    def info(self, *args, **kwargs):  # pragma: no cover - simple stub
        pass

    def warning(self, *args, **kwargs):  # pragma: no cover - simple stub
        pass

    def error(self, *args, **kwargs):  # pragma: no cover - simple stub
        pass


class _RecordingTagIndex:
    def __init__(self):
        self.records: dict[str, dict[str, set[str]]] = {}

    def add_tags(self, asset_id: str, layer_id: str, tags: set[str]):
        layer_records = self.records.setdefault(asset_id, {})
        tag_set = layer_records.setdefault(layer_id, set())
        tag_set.update(tags)


class _StubRepository:
    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def get_path_by_id(self, asset_id: str) -> str | None:
        return self._mapping.get(asset_id)


class _StubVisionService:
    def __init__(self, tags: list[str]):
        self._tags = tags
        self.calls: list[tuple[str, str]] = []

    def generate_tags(self, path: str, media_type: str):
        self.calls.append((path, media_type))
        return list(self._tags)


class _StubFramework:
    def __init__(self, services: dict[str, object]):
        self._services = services
        self.log_manager = services.get("log_manager")

    def get_service(self, service_id: str):
        return self._services.get(service_id)


class AIQuickGeneratorTests(unittest.TestCase):
    def _build_generator(self, services: dict[str, object]) -> AIQuickGenerator:
        services.setdefault("log_manager", _StubLog())
        framework = _StubFramework(services)
        services.setdefault("tag_index_service", _RecordingTagIndex())
        services.setdefault("asset_repository", _StubRepository({}))
        return AIQuickGenerator(framework, {"id": "ai_quick"})

    def test_process_asset_detects_image_without_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset_path = base / "PortraitAsset.bin"
            image = Image.new("RGB", (64, 128), color=(120, 45, 200))
            image.save(asset_path, format="JPEG")

            repository = _StubRepository({"img-001": str(asset_path)})
            tag_index = _RecordingTagIndex()
            generator = self._build_generator(
                {
                    "asset_repository": repository,
                    "tag_index_service": tag_index,
                }
            )

            generator.process_asset("img-001")

            tags = tag_index.records["img-001"]["ai_quick"]
            self.assertIn("image", tags)
            self.assertIn("orientation:portrait", tags)
            self.assertIn("format:jpeg", tags)
            self.assertIn("resolution:64x128", tags)
            self.assertIn("portrait", tags)
            self.assertNotIn("unknown", tags)

    def test_process_asset_handles_non_media_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset_path = base / "notes.data"
            asset_path.write_text("plain text content", encoding="utf-8")

            repository = _StubRepository({"doc-1": str(asset_path)})
            tag_index = _RecordingTagIndex()
            generator = self._build_generator(
                {
                    "asset_repository": repository,
                    "tag_index_service": tag_index,
                }
            )

            generator.process_asset("doc-1")

            tags = tag_index.records["doc-1"]["ai_quick"]
            self.assertIn("unknown", tags)
            self.assertNotIn("image", tags)
            self.assertNotIn("video", tags)

    def test_process_asset_adds_video_tags_when_probe_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset_path = base / "movie_capture.bin"
            asset_path.write_bytes(b"video data placeholder")

            repository = _StubRepository({"vid-01": str(asset_path)})
            tag_index = _RecordingTagIndex()
            generator = self._build_generator(
                {
                    "asset_repository": repository,
                    "tag_index_service": tag_index,
                }
            )

            metadata = {
                "width": "1920",
                "height": "1080",
                "duration": "12.5",
                "codec_name": "h264",
                "codec_type": "video",
            }

            with mock.patch.object(
                AIQuickGenerator, "_probe_video_metadata", return_value=metadata
            ):
                generator.process_asset("vid-01")

            tags = tag_index.records["vid-01"]["ai_quick"]
            self.assertIn("video", tags)
            self.assertIn("resolution:1920x1080", tags)
            self.assertIn("orientation:landscape", tags)
            self.assertIn("duration:short", tags)
            self.assertIn("codec:h264", tags)

    def test_process_asset_uses_vision_service_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset_path = base / "dog.bin"
            image = Image.new("RGB", (128, 64), color=(10, 200, 150))
            image.save(asset_path, format="PNG")

            repository = _StubRepository({"img-vision": str(asset_path)})
            tag_index = _RecordingTagIndex()
            vision = _StubVisionService(["clip:dog", "confidence:high"])

            generator = self._build_generator(
                {
                    "asset_repository": repository,
                    "tag_index_service": tag_index,
                    "vision_tag_service": vision,
                }
            )

            generator.process_asset("img-vision")

            tags = tag_index.records["img-vision"]["ai_quick"]
            self.assertIn("clip:dog", tags)
            self.assertIn("confidence:high", tags)
            self.assertTrue(vision.calls)
            call_path, media_type = vision.calls[0]
            self.assertEqual(Path(call_path), asset_path)
            self.assertEqual(media_type, "image")


if __name__ == "__main__":  # pragma: no cover - unittest boilerplate
    unittest.main()
