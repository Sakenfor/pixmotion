
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, Set

try:  # pragma: no cover - Pillow is an optional dependency at runtime
    from PIL import Image, UnidentifiedImageError
except Exception:  # pragma: no cover - gracefully degrade without Pillow
    Image = None  # type: ignore[assignment]

    class UnidentifiedImageError(Exception):
        """Fallback error type when Pillow is unavailable."""

from .base_generator import BaseLayerGenerator


class AIQuickGenerator(BaseLayerGenerator):
    """Cheap heuristic 'AI quick' generator with lightweight media inspection."""

    _FFPROBE_TIMEOUT = 2.0

    def process_asset(self, asset_id: str) -> None:
        path = None
        if self.repository:
            path = self.repository.get_path_by_id(asset_id)

        tags: set[str] = set()
        if path:
            tags.update(self._tags_from_filename(path))
            media_tags = self._detect_image_tags(path)
            media_type = "image" if media_tags else None
            if not media_tags:
                media_tags = self._detect_video_tags(path)
                if media_tags:
                    media_type = "video"
            if media_tags:
                tags.update(media_tags)
                tags.update(self._generate_model_tags(path, media_type or ""))

        if not tags:
            tags.add("unknown")

        dest_layer_id = None
        if isinstance(self.layer, dict):
            dest_layer_id = self.layer.get("id")
        self.tag_index.add_tags(asset_id, dest_layer_id or "ai_quick", tags)

    # --- Internal helpers -------------------------------------------------

    def _tags_from_filename(self, path: str) -> set[str]:
        lower = Path(path).name.lower()
        tags: set[str] = set()
        if any(x in lower for x in ("portrait", "headshot", "face")):
            tags.add("portrait")
        if any(x in lower for x in ("dog", "cat", "pet")):
            tags.add("animal")
        if any(x in lower for x in ("landscape", "scenery")):
            tags.add("landscape")
        return tags

    def _detect_image_tags(self, path: str) -> set[str]:
        if Image is None:
            return set()
        try:
            with Image.open(path) as img:
                img.load()
                width, height = img.size
                fmt = (img.format or "").lower()
                mode = img.mode or ""

                tags: set[str] = {"image"}
                if fmt:
                    tags.add(f"format:{fmt}")
                if width and height:
                    tags.add(f"resolution:{width}x{height}")
                    orientation = self._orientation_from_dims(width, height)
                    tags.add(f"orientation:{orientation}")
                bands = {band.upper() for band in img.getbands()}
                if "A" in bands:
                    tags.add("has_alpha")
                if mode in {"L", "LA"}:
                    tags.add("grayscale")
                return tags
        except (FileNotFoundError, UnidentifiedImageError, OSError):
            return set()
        return set()

    def _detect_video_tags(self, path: str) -> set[str]:
        metadata = self._probe_video_metadata(path)
        if not metadata:
            return set()

        tags: set[str] = {"video"}
        width = self._safe_int(metadata.get("width"))
        height = self._safe_int(metadata.get("height"))
        if width and height:
            tags.add(f"resolution:{width}x{height}")
            orientation = self._orientation_from_dims(width, height)
            tags.add(f"orientation:{orientation}")

        duration = self._safe_float(metadata.get("duration"))
        if duration is not None:
            tags.add(self._duration_bucket(duration))

        codec = metadata.get("codec_name") or metadata.get("codec")
        if isinstance(codec, str) and codec:
            tags.add(f"codec:{codec.lower()}")
        return tags

    def _probe_video_metadata(self, path: str) -> dict[str, object] | None:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration,codec_name,codec_type",
            "-of",
            "json",
            path,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=False,
                text=True,
                timeout=self._FFPROBE_TIMEOUT,
            )
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            return None
        if result.returncode != 0:
            return None
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return None

        streams = payload.get("streams")
        if not streams:
            return None
        stream = streams[0] or {}
        codec_type = stream.get("codec_type")
        if codec_type and codec_type != "video":
            return None
        return stream

    def _generate_model_tags(self, path: str, media_type: str) -> set[str]:
        if not media_type:
            return set()
        vision_service = None
        try:
            vision_service = self.framework.get_service("vision_tag_service")
        except Exception:
            vision_service = None
        if not vision_service:
            return set()

        try:
            predicted: Iterable[str] | None = vision_service.generate_tags(
                path, media_type=media_type
            )
        except Exception:
            if getattr(self.log, "warning", None):
                self.log.warning(
                    "vision_tag_service failed to tag %s", path, exc_info=True
                )
            return set()

        tags: Set[str] = set()
        if not predicted:
            return tags
        for tag in predicted:
            if isinstance(tag, str) and tag:
                tags.add(tag)
        return tags

    @staticmethod
    def _orientation_from_dims(width: int, height: int) -> str:
        if width == height:
            return "square"
        return "landscape" if width > height else "portrait"

    @staticmethod
    def _safe_int(value: object) -> int | None:
        try:
            if value is None:
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: object) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _duration_bucket(seconds: float) -> str:
        if seconds < 5:
            bucket = "micro"
        elif seconds < 30:
            bucket = "short"
        elif seconds < 120:
            bucket = "medium"
        else:
            bucket = "long"
        return f"duration:{bucket}"
