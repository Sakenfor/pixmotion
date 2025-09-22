from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

from .base_generator import BaseLayerGenerator


class AIDeepGenerator(BaseLayerGenerator):
    """Run a lightweight emotion classifier driven by curated model data."""

    MODEL_RELATIVE_PATH = Path("data/models/emotion_model.json")

    def __init__(self, framework, layer_desc: Dict[str, object]):
        super().__init__(framework, layer_desc)
        self._model_path = self.project_root / self.MODEL_RELATIVE_PATH
        self._model = self._load_model(self._model_path)
        self._label_lookup: Dict[str, Dict[str, object]] = {}
        if self._model:
            labels = self._model.get("labels", [])
            self._label_lookup = {entry["id"]: entry for entry in labels if "id" in entry}

    def _load_model(self, path: Path) -> Dict[str, object] | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            self.log.error("AI Deep model missing at %s", path)
            return None
        except Exception as exc:  # pragma: no cover - defensive logging
            self.log.error("Failed to load AI Deep model: %s", exc, exc_info=True)
            return None

        required = {"features", "labels", "weights"}
        if not required.issubset(data):
            self.log.error("AI Deep model at %s missing required keys", path)
            return None
        return data

    def process_asset(self, asset_id: str) -> None:
        layer_id = "ai_deep"
        if isinstance(self.layer, dict):
            layer_id = self.layer.get("id", layer_id)

        quick_tags: set[str] = set()
        if self.tag_index:
            quick_layer = self.tag_index.get_layers_for_asset(asset_id).get("ai_quick", {})
            quick_tags = {str(tag).lower() for tag in quick_layer.get("tags", [])}

        try:
            if not self._model:
                raise RuntimeError("deep model not loaded")
            if not self.repository:
                raise RuntimeError("asset repository unavailable")

            asset_path = self.repository.get_path_by_id(asset_id)
            if not asset_path:
                raise FileNotFoundError(f"No file path for asset {asset_id}")

            features = self._extract_features(Path(asset_path))
            label, distribution = self._predict(features)
            tags = self._build_tags(label, quick_tags)
            if not tags:
                raise RuntimeError("model returned empty tag set")
            meta = self._build_meta(label, distribution, features, Path(asset_path))

            if self.tag_index:
                self.tag_index.set_tags(asset_id, layer_id, tags, meta=meta)
        except Exception as exc:  # pragma: no cover - exercised in dedicated test
            self.log.error("AI Deep inference failed for %s: %s", asset_id, exc)
            if self.tag_index:
                self.tag_index.set_tags(
                    asset_id,
                    layer_id,
                    {"needs_review"},
                    meta={"error": str(exc)},
                )

    def _extract_features(self, path: Path) -> np.ndarray:
        try:
            with Image.open(path) as img:
                rgb = img.convert("RGB")
                array = np.asarray(rgb, dtype=np.float32) / 255.0
        except FileNotFoundError:
            raise
        except UnidentifiedImageError as exc:
            raise ValueError("unsupported image format") from exc

        if array.size == 0:
            raise ValueError("empty image data")

        brightness = float(array.mean())
        warmth = float((array[..., 0] - array[..., 2]).mean())
        contrast = float(array.std())
        return np.array([brightness, warmth, contrast], dtype=np.float32)

    def _predict(self, features: np.ndarray) -> Tuple[str, Dict[str, float]]:
        weights = self._model.get("weights", {})
        scores: Dict[str, float] = {}
        for label, params in weights.items():
            coeffs = np.array(params.get("weights", []), dtype=np.float32)
            if coeffs.shape[0] != features.shape[0]:
                raise ValueError(f"feature dimension mismatch for label {label}")
            bias = float(params.get("bias", 0.0))
            scores[label] = bias + float(np.dot(coeffs, features))

        if not scores:
            raise RuntimeError("model returned no scores")

        max_score = max(scores.values())
        exp_scores = {label: math.exp(score - max_score) for label, score in scores.items()}
        total = sum(exp_scores.values())
        distribution = {label: value / total for label, value in exp_scores.items()}
        best_label = max(distribution, key=distribution.get)
        return best_label, distribution

    def _build_tags(self, label: str, quick_tags: Iterable[str]) -> set[str]:
        curated: set[str] = set()
        entry = self._label_lookup.get(label)
        if entry:
            primary = entry.get("tag")
            if primary:
                curated.add(str(primary))
            for extra in entry.get("extras", []):
                if extra:
                    curated.add(str(extra))

        quick_map = {
            "portrait": "subject:person",
            "animal": "subject:animal",
            "video": "format:video",
            "image": "format:image",
        }
        for tag in quick_tags:
            mapped = quick_map.get(str(tag).lower())
            if mapped:
                curated.add(mapped)
        return curated

    def _build_meta(
        self,
        label: str,
        distribution: Dict[str, float],
        features: np.ndarray,
        asset_path: Path,
    ) -> Dict[str, object]:
        entry = self._label_lookup.get(label, {})
        feature_names = list(self._model.get("features", []))
        feature_values = [round(float(v), 4) for v in features.tolist()]
        feature_map = {
            name: value for name, value in zip(feature_names, feature_values)
        }

        tag_distribution = {}
        for lbl, prob in distribution.items():
            tag_name = self._label_lookup.get(lbl, {}).get("tag", lbl)
            tag_distribution[str(tag_name)] = round(float(prob), 4)

        meta: Dict[str, object] = {
            "model_name": self._model.get("name", "curated_emotion_classifier"),
            "model_version": self._model.get("version"),
            "model_path": str(self._model_path),
            "predicted_label": label,
            "predicted_tag": entry.get("tag", label),
            "confidence": round(float(distribution[label]), 4),
            "distribution": tag_distribution,
            "features": feature_map,
            "asset_path": str(asset_path),
        }
        return meta
