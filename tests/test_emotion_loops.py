from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from framework.manifests import EmotionIntentConfig, EmotionPackageManifest
from plugins.assets.emotion_service import EmotionClipAnalyzer, EmotionAnalyzerConfig
from plugins.assets.emotion_selector import EmotionLoopSelector


class _StubLog:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class _StubEvents:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, name, callback):
        self._subscribers.setdefault(name, []).append(callback)

    def publish(self, name, **kwargs):
        for callback in self._subscribers.get(name, []):
            callback(**kwargs)


class _StubAssetManager:
    def __init__(self, packages):
        self._packages = packages

    @property
    def emotion_packages(self):  # pragma: no cover - simple accessor
        return self._packages


class _StubAssetService:
    def __init__(self, paths):
        self._paths = paths

    def add_asset(self, path):  # pragma: no cover - not used in selector test
        raise NotImplementedError

    def get_asset_path(self, asset_id: str) -> str | None:
        return self._paths.get(asset_id)


class _StubRepository:
    def __init__(self, clips):
        self._clips = clips

    def list_clips(self, *, package_uuid=None, package_uuids=None, intents=None):
        intents = set(intents or [])
        matches = []
        for clip in self._clips:
            if package_uuid and clip.package_uuid != package_uuid:
                continue
            if package_uuids and clip.package_uuid not in package_uuids:
                continue
            if intents and clip.intent not in intents:
                continue
            matches.append(clip)
        return matches


class _StubFramework:
    def __init__(self, services):
        self._services = services

    def get_service(self, service_id):
        return self._services.get(service_id)


class EmotionClipAnalyzerTests(unittest.TestCase):
    def test_analyzer_extracts_basic_metrics(self) -> None:
        analyzer = EmotionClipAnalyzer()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "sample.mp4"
            writer = cv2.VideoWriter(
                str(output), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (32, 32)
            )
            for idx in range(45):
                value = 80 + idx
                frame = np.full((32, 32, 3), value, dtype=np.uint8)
                writer.write(frame)
            writer.release()

            result = analyzer.analyze(output)
            self.assertIsNotNone(result.duration)
            self.assertGreater(result.duration or 0, 1.0)
            self.assertIsNotNone(result.loop_end)
            self.assertIsNotNone(result.metadata)
            self.assertEqual(result.metadata.get("frame_count"), 45)
            self.assertIn("loop_similarity", result.metadata)
            self.assertIn("face_detection_ratio", result.metadata)
            self.assertIn("expression_label", result.metadata)
            self.assertIn("expression_confidence", result.metadata)
            self.assertTrue(result.tags)
            self.assertIn("no_face", result.tags)

    def test_config_from_dict_parses_values(self) -> None:
        config = EmotionAnalyzerConfig.from_dict(
            {
                "face_cascade_path": "custom_cascade.xml",
                "emotion_model_path": "model.onnx",
                "emotion_labels": "neutral, happy, sad",
                "emotion_input_size": "256",
                "max_frames": "480",
                "face_stride": "4",
            }
        )
        self.assertEqual(config.face_cascade_path, "custom_cascade.xml")
        self.assertEqual(config.emotion_model_path, "model.onnx")
        self.assertEqual(config.emotion_labels, ["neutral", "happy", "sad"])
        self.assertEqual(config.emotion_input_size, 256)
        self.assertEqual(config.max_frames, 480)
        self.assertEqual(config.face_stride, 4)


class EmotionLoopSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        manifest = EmotionPackageManifest(
            uuid="pkg-1",
            name="Evening Content",
            type="emotion_package",
            version="1.0",
            tags=[],
            path="/virtual/assets",
            manifest_path="/virtual/assets/asset.json",
            metadata={},
            persona_ids=["npc_a"],
            context_tags=["evening", "indoor"],
            supported_tones=["content", "calm"],
            intents={
                "content_idle": EmotionIntentConfig(paths=["idle"], weight=1.0, metadata={})
            },
        )
        self.manifest = manifest

        clip_a = SimpleNamespace(
            asset_id="asset_a",
            package_uuid="pkg-1",
            intent="content_idle",
            rel_path="content_idle/a.mp4",
            loop_start=0.0,
            loop_end=1.8,
            duration=1.8,
            motion=0.03,
            confidence=0.6,
            tags=["calm"],
            analysis_metadata={},
        )
        clip_b = SimpleNamespace(
            asset_id="asset_b",
            package_uuid="pkg-1",
            intent="content_idle",
            rel_path="content_idle/b.mp4",
            loop_start=0.0,
            loop_end=2.5,
            duration=2.5,
            motion=0.05,
            confidence=0.92,
            tags=["smile"],
            analysis_metadata={"expression_confidence": 0.9},
        )

        repo = _StubRepository([clip_a, clip_b])
        assets = _StubAssetService(
            {
                "asset_a": "/virtual/assets/content_idle/a.mp4",
                "asset_b": "/virtual/assets/content_idle/b.mp4",
            }
        )
        events = _StubEvents()
        services = {
            "log_manager": _StubLog(),
            "asset_manager": _StubAssetManager({manifest.uuid: manifest}),
            "event_manager": events,
        }
        framework = _StubFramework(services)
        services["framework"] = framework
        selector = EmotionLoopSelector(framework, repo, assets)
        self.selector = selector

    def test_select_clip_prefers_high_confidence(self) -> None:
        result = self.selector.select_clip(
            persona_id="npc_a",
            intent="content_idle",
            tone="calm",
            context_tags=["evening"],
            seed=42,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["asset_id"], "asset_b")
        self.assertIn("package", result)

    def test_recent_assets_are_deprioritized(self) -> None:
        first = self.selector.select_clip(
            persona_id="npc_a", intent="content_idle", seed=5
        )
        self.assertIsNotNone(first)
        second = self.selector.select_clip(
            persona_id="npc_a",
            intent="content_idle",
            recent_asset_ids=[first["asset_id"]],
            seed=7,
        )
        self.assertIsNotNone(second)
        self.assertNotEqual(second["asset_id"], first["asset_id"])


if __name__ == "__main__":
    unittest.main()
