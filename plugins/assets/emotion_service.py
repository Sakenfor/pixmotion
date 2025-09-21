from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Set, Tuple

import cv2
import numpy as np

from framework.manifests import EmotionIntentConfig, EmotionPackageManifest

from .emotion_repository import EmotionClipRepository

if TYPE_CHECKING:
    from .services import AssetService  # pragma: no cover


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}



@dataclass(slots=True)
class AnalysisResult:
    loop_start: Optional[float] = None
    loop_end: Optional[float] = None
    duration: Optional[float] = None
    motion: Optional[float] = None
    confidence: Optional[float] = None
    expression: Optional[str] = None
    expression_confidence: Optional[float] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, object]] = None


@dataclass(slots=True)
class EmotionAnalyzerConfig:
    face_cascade_path: Optional[str] = None
    emotion_model_path: Optional[str] = None
    emotion_labels: List[str] = field(default_factory=list)
    emotion_input_size: int = 224
    emotion_mean: Tuple[float, float, float] = (0.485, 0.456, 0.406)
    emotion_std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    max_frames: int = 360
    face_stride: int = 3

    @classmethod
    def from_dict(cls, data: Dict[str, object] | None) -> "EmotionAnalyzerConfig":
        data = dict(data or {})

        labels = data.get("emotion_labels")
        if isinstance(labels, str):
            labels = [item.strip() for item in labels.split(',') if item.strip()]
        elif not isinstance(labels, (list, tuple)):
            labels = []

        def _normalise_triplet(value, fallback):
            seq = value if isinstance(value, (list, tuple)) else fallback
            seq = list(seq)
            if len(seq) != len(fallback):
                seq = list(fallback)
            try:
                return tuple(float(x) for x in seq)
            except (TypeError, ValueError):
                return fallback

        emotion_mean = _normalise_triplet(data.get("emotion_mean"), (0.485, 0.456, 0.406))
        emotion_std = _normalise_triplet(data.get("emotion_std"), (0.229, 0.224, 0.225))

        def _safe_int(key, default):
            try:
                return int(data.get(key, default) or default)
            except (TypeError, ValueError):
                return default

        return cls(
            face_cascade_path=str(data.get("face_cascade_path") or '') or None,
            emotion_model_path=str(data.get("emotion_model_path") or '') or None,
            emotion_labels=[str(label) for label in labels or []],
            emotion_input_size=_safe_int("emotion_input_size", 224),
            emotion_mean=emotion_mean,
            emotion_std=emotion_std,
            max_frames=_safe_int("max_frames", 360),
            face_stride=_safe_int("face_stride", 3),
        )


class EmotionClipAnalyzer:
    """Derives loop boundaries plus optional face/expression metadata."""

    def __init__(self, *, config: EmotionAnalyzerConfig | None = None) -> None:
        self.config = config or EmotionAnalyzerConfig.from_dict(None)
        self._max_frames = max(60, self.config.max_frames)
        self._face_stride = max(1, self.config.face_stride)
        self._face_cascade = self._load_face_detector(self.config.face_cascade_path)
        (
            self._emotion_net,
            self._emotion_labels,
            self._emotion_input_size,
            self._emotion_mean,
            self._emotion_std,
        ) = self._load_emotion_classifier(self.config)

    def analyze(self, path: Path) -> AnalysisResult:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            return AnalysisResult()

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        duration = float(frame_count / fps) if frame_count and fps else None

        sampled_frames: List[tuple[int, np.ndarray]] = []
        motion_diffs: List[float] = []
        histograms: List[Tuple[int, np.ndarray]] = []

        face_hits = 0
        face_sizes: List[float] = []
        face_centers: List[Tuple[float, float]] = []
        mouth_scores: List[float] = []
        expression_scores: Dict[str, List[float]] = {}

        prev_gray = None
        index = 0
        frame_step = 1

        try:
            while True:
                success, frame = capture.read()
                if not success:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if not sampled_frames:
                    sampled_frames.append((index, gray))
                elif index % frame_step == 0:
                    sampled_frames.append((index, gray))
                    if len(sampled_frames) >= self._max_frames:
                        frame_step = max(1, index // self._max_frames)

                hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                histograms.append((index, hist))

                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    motion_diffs.append(float(cv2.mean(diff)[0]))
                prev_gray = gray

                if (
                    self._face_cascade is not None
                    and (index % self._face_stride == 0)
                ):
                    faces = self._face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.2,
                        minNeighbors=5,
                        minSize=(48, 48),
                    )
                    if len(faces) > 0:
                        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                        face_hits += 1
                        size_ratio = (w * h) / float(gray.shape[0] * gray.shape[1])
                        face_sizes.append(size_ratio)
                        face_centers.append((x + w / 2.0, y + h / 2.0))
                        mouth_region = gray[y + int(h * 0.55) : y + h, x : x + w]
                        upper_region = gray[y : y + int(h * 0.45), x : x + w]
                        if mouth_region.size > 0 and upper_region.size > 0:
                            mouth_score = float(
                                np.abs(np.mean(mouth_region) - np.mean(upper_region))
                            )
                            mouth_scores.append(mouth_score)
                        if self._emotion_net is not None:
                            label, score = self._infer_expression(frame[y : y + h, x : x + w])
                            if label:
                                expression_scores.setdefault(label, []).append(score or 0.0)
                index += 1
        finally:
            capture.release()

        if not sampled_frames:
            return AnalysisResult(duration=duration)

        first_index, first_gray = sampled_frames[0]
        first_hist = next((h for idx, h in histograms if idx == first_index), None)

        best_similarity = 0.0
        best_index = None
        loop_end = duration

        for idx, hist in histograms[2:]:
            similarity = (
                float(cv2.compareHist(first_hist, hist, cv2.HISTCMP_CORREL))
                if first_hist is not None
                else 0.0
            )
            if similarity > best_similarity:
                best_similarity = similarity
                best_index = idx

        if best_index is not None and fps:
            loop_end = float(best_index / fps)

        confidence = None
        if best_similarity > 0:
            confidence = max(0.0, min(1.0, (best_similarity + 1.0) / 2.0))

        motion_avg = float(np.mean(motion_diffs)) if motion_diffs else None
        motion_std = float(np.std(motion_diffs)) if motion_diffs else None
        motion_norm = (motion_avg / 255.0) if motion_avg is not None else None

        face_ratio = face_hits / max(1, len(sampled_frames))
        avg_face_size = float(np.mean(face_sizes)) if face_sizes else None
        head_motion = None
        if face_centers:
            centers = np.array(face_centers)
            head_motion = float(
                np.linalg.norm(centers.max(axis=0) - centers.min(axis=0))
                / max(first_gray.shape)
            )
        mouth_score = float(np.mean(mouth_scores)) if mouth_scores else None

        expression_label = None
        expression_conf = None
        if expression_scores:
            expression_label, scores = max(
                expression_scores.items(), key=lambda item: np.mean(item[1])
            )
            expression_conf = float(np.mean(scores))

        tags: List[str] = []
        if motion_norm is not None:
            if motion_norm < 0.01:
                tags.append('still')
            elif motion_norm < 0.03:
                tags.append('calm')
            elif motion_norm < 0.07:
                tags.append('animated')
            else:
                tags.append('energetic')
        if face_ratio > 0.3:
            tags.append('has_face')
        else:
            tags.append('no_face')
        if expression_label:
            tags.append(f'expr:{expression_label}')
        elif face_ratio > 0:
            tags.append('neutral_face')
        if mouth_score is not None and mouth_score > 8:
            tags.append('smiling')
        if head_motion and head_motion > 0.12:
            tags.append('head_motion')
        folder_tag = path.parent.name.strip().lower()
        if folder_tag and folder_tag not in tags:
            tags.append(folder_tag)

        metadata: Dict[str, object] = {
            'frame_count': frame_count,
            'fps': fps,
            'sampled_frames': len(sampled_frames),
            'loop_frame_index': best_index,
            'loop_similarity': best_similarity,
            'motion_avg': motion_avg,
            'motion_stddev': motion_std,
            'motion_norm': motion_norm,
            'face_detection_ratio': face_ratio,
            'avg_face_size': avg_face_size,
            'head_motion': head_motion,
            'expression_score': mouth_score,
            'expression_label': expression_label,
            'expression_confidence': expression_conf,
            'source_stem': path.stem,
        }

        return AnalysisResult(
            loop_start=0.0 if loop_end is not None else None,
            loop_end=loop_end,
            duration=duration,
            motion=motion_norm,
            confidence=confidence,
            expression=expression_label,
            expression_confidence=expression_conf,
            tags=tags or None,
            metadata=metadata,
        )

    def _load_face_detector(self, cascade_path: Optional[str]):
        if cascade_path:
            file_path = Path(cascade_path)
            if file_path.exists():
                cascade = cv2.CascadeClassifier(str(file_path))
                if not cascade.empty():
                    return cascade
        if hasattr(cv2, 'data'):
            default_path = Path(cv2.data.haarcascades) / 'haarcascade_frontalface_default.xml'
            if default_path.exists():
                cascade = cv2.CascadeClassifier(str(default_path))
                if not cascade.empty():
                    return cascade
        return None

    def _load_emotion_classifier(self, config: EmotionAnalyzerConfig):
        model_path = config.emotion_model_path
        if not model_path:
            return None, [], config.emotion_input_size, config.emotion_mean, config.emotion_std
        model_file = Path(model_path)
        if not model_file.exists():
            return None, [], config.emotion_input_size, config.emotion_mean, config.emotion_std
        try:
            net = cv2.dnn.readNetFromONNX(str(model_file))
        except Exception:
            return None, [], config.emotion_input_size, config.emotion_mean, config.emotion_std
        labels = list(config.emotion_labels)
        return net, labels, config.emotion_input_size, config.emotion_mean, config.emotion_std

    def _infer_expression(self, face_bgr: np.ndarray) -> Tuple[Optional[str], Optional[float]]:
        if self._emotion_net is None or face_bgr.size == 0:
            return None, None
        face = cv2.resize(face_bgr, (self._emotion_input_size, self._emotion_input_size))
        face = face.astype('float32') / 255.0
        mean = np.array(self._emotion_mean, dtype=np.float32).reshape(1, 1, 3)
        std = np.array(self._emotion_std, dtype=np.float32).reshape(1, 1, 3)
        face = (face - mean) / std
        face = face.transpose(2, 0, 1)
        blob = np.expand_dims(face, axis=0)
        try:
            self._emotion_net.setInput(blob)
            scores = self._emotion_net.forward()
        except Exception:
            return None, None
        scores = scores.flatten()
        if scores.size == 0:
            return None, None
        exp_scores = np.exp(scores - np.max(scores))
        probs = exp_scores / np.sum(exp_scores)
        idx = int(np.argmax(probs))
        label = (
            self._emotion_labels[idx]
            if idx < len(self._emotion_labels) and self._emotion_labels
            else str(idx)
        )
        return label, float(probs[idx])



class EmotionPackageService:
    """Coordinates emotion-package ingestion and analytics persistence."""

    def __init__(
        self,
        framework,
        asset_service: "AssetService",
        clip_repository: EmotionClipRepository,
        analyzer: EmotionClipAnalyzer | None = None,
    ) -> None:
        self.framework = framework
        self.asset_service = asset_service
        self.repository = clip_repository
        self.analyzer = analyzer or EmotionClipAnalyzer(config=self._load_analyzer_config())

        self.log = framework.get_service("log_manager")
        self.events = framework.get_service("event_manager")
        self.asset_manager = framework.get_service("asset_manager")
        self._loop_selector = None

        if self.events:
            self.events.subscribe("shell:ready", self._on_shell_ready)

    def register_selector(self, selector) -> None:
        """Attach the runtime selector so cache invalidation stays in sync."""
        self._loop_selector = selector

    # ------------------------------------------------------------------
    # Public API

    def sync_all_packages(self) -> None:
        manifests = getattr(self.asset_manager, "emotion_packages", {}) or {}
        if not manifests:
            self.log.info("No emotion package manifests discovered.")
            return

        for manifest in manifests.values():
            self.sync_package(manifest)

        if self._loop_selector:
            self._loop_selector.refresh_manifests()

        if self.events:
            self.events.publish("assets:emotion_packages_synced")

    def sync_package_by_uuid(self, package_uuid: str) -> None:
        manifest = (self.asset_manager.emotion_packages or {}).get(package_uuid)
        if not manifest:
            self.log.warning(
                "Requested emotion package %s not found in manifests.", package_uuid
            )
            return
        self.sync_package(manifest)

    # ------------------------------------------------------------------

    def sync_package(self, manifest: EmotionPackageManifest) -> None:
        package_root = Path(manifest.path)
        if not package_root.exists():
            self.log.warning(
                "Emotion package directory missing: %s", package_root.as_posix()
            )
            return

        self.log.info(
            "Syncing emotion package '%s' (%s)", manifest.name or manifest.uuid, manifest.uuid
        )

        for intent_name, intent_cfg in manifest.intents.items():
            self._sync_intent(manifest, package_root, intent_name, intent_cfg)

        if self._loop_selector:
            self._loop_selector.invalidate_package(manifest.uuid)

        if self.events:
            self.events.publish(
                "assets:emotion_package_updated", package_uuid=manifest.uuid
            )

    # ------------------------------------------------------------------

    def _sync_intent(
        self,
        manifest: EmotionPackageManifest,
        package_root: Path,
        intent_name: str,
        intent_cfg: EmotionIntentConfig,
    ) -> None:
        if not intent_cfg.paths:
            self.log.warning(
                "Intent '%s' in package %s has no paths configured.",
                intent_name,
                manifest.uuid,
            )
            return

        seen_asset_ids: Set[str] = set()
        metadata_base: Dict[str, object] = {
            "intent_weight": intent_cfg.weight,
            "package_context": manifest.context_tags,
            "package_tones": manifest.supported_tones,
        }

        for rel_path in intent_cfg.paths:
            resolved = (package_root / rel_path).resolve()
            if not resolved.exists():
                self.log.warning(
                    "Intent '%s' references missing path: %s",
                    intent_name,
                    resolved.as_posix(),
                )
                continue

            for file_path in self._iter_media_files(resolved):
                asset = self.asset_service.add_asset(file_path)
                if not asset:
                    continue

                analysis = self.analyzer.analyze(Path(file_path))
                rel_to_root = os.path.relpath(file_path, package_root)

                self.repository.upsert_clip(
                    asset_id=asset.id,
                    package_uuid=manifest.uuid,
                    intent=intent_name,
                    rel_path=rel_to_root.replace("\\", "/"),
                    loop_start=analysis.loop_start,
                    loop_end=analysis.loop_end,
                    duration=analysis.duration,
                    motion=analysis.motion,
                    confidence=analysis.confidence,
                    tags=analysis.tags,
                    embedding=None,
                    analysis_metadata=self._merge_metadata(metadata_base, analysis.metadata),
                )
                seen_asset_ids.add(asset.id)

        removed = self.repository.remove_missing(
            package_uuid=manifest.uuid,
            intent=intent_name,
            keep_asset_ids=seen_asset_ids,
        )
        if removed:
            self.log.info(
                "Removed %s obsolete emotion clips from %s intent '%s'",
                removed,
                manifest.uuid,
                intent_name,
            )

    # ------------------------------------------------------------------

    def _load_analyzer_config(self) -> EmotionAnalyzerConfig:
        settings = self.framework.get_service("settings_service")
        config_data: Dict[str, object] | None = None
        if settings:
            value = settings.get("emotion_analyzer", None)
            if isinstance(value, dict):
                config_data = value
        return EmotionAnalyzerConfig.from_dict(config_data)
    def _iter_media_files(self, base_path: Path) -> Iterable[str]:
        if base_path.is_file():
            if base_path.suffix.lower() in VIDEO_EXTENSIONS:
                yield str(base_path)
            return

        for path in base_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
                yield str(path)

    def _merge_metadata(
        self,
        base: Dict[str, object],
        extra: Optional[Dict[str, object]],
    ) -> Dict[str, object]:
        merged = dict(base)
        if extra:
            merged.update(extra)
        return merged

    def _on_shell_ready(self, **_: object) -> None:
        self.sync_all_packages()







