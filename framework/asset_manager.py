from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import uuid

from .manifests import (
    AssetManifest,
    EmotionPackageManifest,
    PluginManifest,
)


class AssetManager:
    """Discovers asset and plugin manifests and exposes them to the framework."""

    def __init__(self, log_manager):
        self.log = log_manager
        self._asset_manifests: Dict[str, AssetManifest] = {}
        self._emotion_packages: Dict[str, EmotionPackageManifest] = {}
        self._plugin_manifests: Dict[str, PluginManifest] = {}
        self._errors: List[str] = []

    @property
    def plugin_manifests(self) -> Dict[str, PluginManifest]:
        return dict(self._plugin_manifests)

    @property
    def asset_manifests(self) -> Dict[str, AssetManifest]:
        return dict(self._asset_manifests)

    @property
    def emotion_packages(self) -> Dict[str, EmotionPackageManifest]:
        return dict(self._emotion_packages)

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    def discover(
        self,
        *,
        asset_dirs: Iterable[str] | None = None,
        plugin_dirs: Iterable[Tuple[str, str]] | None = None,
    ) -> None:
        """Scan provided directories for manifest files."""
        self._asset_manifests.clear()
        self._emotion_packages.clear()
        self._plugin_manifests.clear()
        self._errors.clear()

        if asset_dirs:
            for base_path in asset_dirs:
                self._scan_for_asset_manifests(base_path)

        if plugin_dirs:
            for base_path, trust_level in plugin_dirs:
                self._scan_for_plugin_manifests(base_path, trust_level)

    # --- Asset discovery -------------------------------------------------

    def _scan_for_asset_manifests(self, base_path: str) -> None:
        if not os.path.isdir(base_path):
            return

        for root, dirs, files in os.walk(base_path):
            if "asset.json" not in files:
                continue

            manifest_path = os.path.join(root, "asset.json")
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if "uuid" not in data:
                    data["uuid"] = str(uuid.uuid4())
                    Path(manifest_path).write_text(json.dumps(data, indent=2))

                manifest_type = str(data.get("type", "")).strip()
                if manifest_type == "emotion_package":
                    manifest = EmotionPackageManifest.from_dict(
                        data, root_path=root, manifest_path=manifest_path
                    )
                else:
                    manifest = AssetManifest.from_dict(
                        data, root_path=root, manifest_path=manifest_path
                    )
            except Exception as exc:  # noqa: BLE001
                msg = f"Failed to load asset manifest at {manifest_path}: {exc}"
                self.log.error(msg)
                self._errors.append(msg)
                continue

            if manifest.uuid in self._asset_manifests:
                msg = (
                    f"Duplicate asset UUID detected: {manifest.uuid} ({manifest_path})"
                )
                self.log.error(msg)
                self._errors.append(msg)
                continue

            self._asset_manifests[manifest.uuid] = manifest
            if isinstance(manifest, EmotionPackageManifest):
                self._emotion_packages[manifest.uuid] = manifest
            dirs[:] = []  # Stop descending into this directory

    # --- Plugin discovery ------------------------------------------------

    def _scan_for_plugin_manifests(self, base_path: str, trust_level: str) -> None:
        if not os.path.isdir(base_path):
            self.log.info(f"Plugin directory not found, skipping: {base_path}")
            return

        for root, dirs, files in os.walk(base_path):
            if trust_level != "user" and "user" in dirs:
                dirs.remove("user")
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            if "plugin.json" not in files:
                continue

            manifest_path = os.path.join(root, "plugin.json")
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if "uuid" not in data:
                    data["uuid"] = str(uuid.uuid4())
                    Path(manifest_path).write_text(json.dumps(data, indent=2))
                manifest = PluginManifest.from_dict(
                    data,
                    root_path=root,
                    manifest_path=manifest_path,
                    trust_level=trust_level,
                )
            except Exception as exc:  # noqa: BLE001
                msg = f"Failed to load plugin manifest at {manifest_path}: {exc}"
                self.log.error(msg)
                self._errors.append(msg)
                continue

            if not manifest.entry_point:
                msg = f"Plugin manifest missing entry_point: {manifest_path}"
                self.log.error(msg)
                self._errors.append(msg)
                continue

            if manifest.uuid in self._plugin_manifests:
                msg = (
                    f"Duplicate plugin UUID detected: {manifest.uuid} ({manifest_path})"
                )
                self.log.error(msg)
                self._errors.append(msg)
                continue

            self._plugin_manifests[manifest.uuid] = manifest
            dirs[:] = []
