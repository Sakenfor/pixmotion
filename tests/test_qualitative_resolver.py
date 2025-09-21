from __future__ import annotations

import random
import unittest
from typing import Any

from framework.graph_registry import GraphRegistry
from framework.graph_qualitative import QualitativeResolver
from plugins.core.graph_scales import DEFAULT_QUALITATIVE_SCALES


class _DummyLog:
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass


class QualitativeResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = GraphRegistry(_DummyLog())
        for scale in DEFAULT_QUALITATIVE_SCALES:
            self.registry.register_qualitative_scale(scale, plugin_uuid="test")
        self.resolver = QualitativeResolver(self.registry)

    def test_resolve_explicit_descriptor_midpoint(self) -> None:
        result = self.resolver.resolve("core.trust", "open", randomize=False, context_overrides={"descriptors": {"open": {"jitter": 0}}})
        self.assertIsNotNone(result)
        assert result is not None  # for type checkers
        self.assertEqual("open", result.descriptor)
        self.assertGreaterEqual(result.value, 55)
        self.assertLessEqual(result.value, 75)

    def test_resolve_uses_default_descriptor(self) -> None:
        result = self.resolver.resolve("core.arousal", None, randomize=False, context_overrides={"descriptors": {"calm": {"jitter": 0}}})
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("calm", result.descriptor)
        self.assertGreaterEqual(result.value, 10)
        self.assertLessEqual(result.value, 35)

    def test_resolve_supports_alias(self) -> None:
        result = self.resolver.resolve("core.arousal", "spark", randomize=False, context_overrides={"descriptors": {"flirty": {"jitter": 0}}})
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("flirty", result.descriptor)
        self.assertGreaterEqual(result.value, 60)
        self.assertLessEqual(result.value, 80)

    def test_persona_override_adjusts_range(self) -> None:
        persona_settings = {
            "qualitative_overrides": {
                "core.trust": {
                    "descriptors": {
                        "open": {
                            "range": [70, 80],
                            "jitter": 0,
                        }
                    }
                }
            }
        }
        result = self.resolver.resolve(
            "core.trust",
            "open",
            persona_settings=persona_settings,
            randomize=False,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreaterEqual(result.value, 70)
        self.assertLessEqual(result.value, 80)

    def test_randomized_values_stay_in_range(self) -> None:
        rng = random.Random(1234)
        values = []
        for _ in range(25):
            result = self.resolver.resolve("core.trust", "wary", rng=rng)
            self.assertIsNotNone(result)
            assert result is not None
            values.append(result.value)
        for value in values:
            self.assertGreaterEqual(value, 10)
            self.assertLessEqual(value, 40)


if __name__ == "__main__":
    unittest.main()
