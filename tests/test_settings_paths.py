from __future__ import annotations

import json
import tempfile
from pathlib import Path

import unittest

from plugins.core.services import SettingsService


class _StubLog:
    def info(self, *args, **kwargs):  # pragma: no cover - behaviour not critical for tests
        pass

    def warning(self, *args, **kwargs):  # pragma: no cover - behaviour not critical for tests
        pass

    def error(self, *args, **kwargs):  # pragma: no cover - behaviour not critical for tests
        pass


class _StubFramework:
    def __init__(self, project_root: Path):
        self._project_root = project_root
        self._log = _StubLog()

    def get_project_root(self) -> str:
        return str(self._project_root)

    def get_service(self, name: str):
        if name == "log_manager":
            return self._log
        return None


class SettingsServicePathTests(unittest.TestCase):
    def test_resolve_user_path_respects_relative_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            settings_path = project_root / "app_settings.json"
            payload = {"user_data_root": "user_data"}
            settings_path.write_text(json.dumps(payload), encoding="utf-8")

            service = SettingsService(_StubFramework(project_root))

            generated_dir = Path(service.resolve_user_path("generated", "media"))
            self.assertTrue(generated_dir.is_dir())
            self.assertTrue(str(generated_dir).startswith(str(project_root / "user_data")))

            nested_file = Path(
                service.resolve_user_path("generated", "clips", "example.mp4")
            )
            self.assertEqual(nested_file.parent, generated_dir.parent / "clips")
            self.assertTrue(nested_file.parent.is_dir())

            override_root = project_root / "custom"
            resolved_override = Path(service.resolve_user_path(str(override_root)))
            self.assertEqual(resolved_override, override_root)
            self.assertTrue(resolved_override.exists())

    def test_default_user_data_root_is_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            settings_path = project_root / "app_settings.json"
            settings_path.write_text("{}", encoding="utf-8")

            service = SettingsService(_StubFramework(project_root))
            resolved_root = Path(service.resolve_user_path())

            self.assertEqual(resolved_root, project_root / "data")
            self.assertTrue(resolved_root.is_dir())


if __name__ == "__main__":  # pragma: no cover - convenience for local runs
    unittest.main()
