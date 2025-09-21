from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence, Tuple

from framework.manifests import EmotionIntentConfig, EmotionPackageManifest

from ..repositories import EmotionClipRepository

if TYPE_CHECKING:
    from .asset_service import AssetService  # pragma: no cover
    from framework.asset_manager import AssetManager  # pragma: no cover


_SHARED_PERSONA = "__shared__"


@dataclass(slots=True)
class ClipPayload:
    asset_id: str
    package_uuid: str
    intent: str
    rel_path: str
    loop_start: float | None
    loop_end: float | None
    duration: float | None
    motion: float | None
    confidence: float | None
    tags: List[str]
    analysis_metadata: Dict[str, object]


class EmotionLoopSelector:
    """Chooses the best loop clip for a persona/intent based on analytics."""

    def __init__(
        self,
        framework,
        repository: EmotionClipRepository,
        asset_service: "AssetService",
    ) -> None:
        self.framework = framework
        self.repository = repository
        self.asset_service = asset_service
        self._log = framework.get_service("log_manager")
        self._asset_manager: Optional[AssetManager] = framework.get_service(
            "asset_manager"
        )
        self._events = framework.get_service("event_manager")

        self._packages: Dict[str, EmotionPackageManifest] = {}
        self._package_meta: Dict[str, Dict[str, object]] = {}
        self._persona_index: Dict[str, List[str]] = {}
        self._clip_cache: Dict[Tuple[str, str], List[ClipPayload]] = {}
        self._recent_history: Dict[Tuple[str, str], List[str]] = {}
        self._rng = random.Random()

        if self._events:
            self._events.subscribe(
                "assets:emotion_packages_synced", self._on_packages_synced
            )
            self._events.subscribe(
                "assets:emotion_package_updated", self._on_package_updated
            )

        self.refresh_manifests()

    # ------------------------------------------------------------------
    # Public API

    def refresh_manifests(self) -> None:
        self._packages = {}
        self._package_meta = {}
        self._persona_index = {}
        if not self._asset_manager:
            self._asset_manager = self.framework.get_service("asset_manager")
        manifests = getattr(self._asset_manager, "emotion_packages", {}) if self._asset_manager else {}
        manifests = manifests or {}
        for uuid, manifest in manifests.items():
            self._packages[uuid] = manifest
            meta = {
                "context": {tag.lower() for tag in manifest.context_tags},
                "tones": {tone.lower() for tone in manifest.supported_tones},
                "intents": manifest.intents,
            }
            self._package_meta[uuid] = meta
            persona_ids = manifest.persona_ids or [_SHARED_PERSONA]
            for persona in persona_ids:
                self._persona_index.setdefault(persona, []).append(uuid)
        # Drop caches for packages that no longer exist
        to_remove = [key for key in self._clip_cache if key[0] not in self._packages]
        for key in to_remove:
            self._clip_cache.pop(key, None)

    def invalidate_package(self, package_uuid: str) -> None:
        keys = [key for key in self._clip_cache if key[0] == package_uuid]
        for key in keys:
            self._clip_cache.pop(key, None)

    def select_clip(
        self,
        *,
        persona_id: str | None,
        intent: str,
        tone: str | None = None,
        context_tags: Iterable[str] | None = None,
        recent_asset_ids: Sequence[str] | None = None,
        avoid_asset_ids: Sequence[str] | None = None,
        seed: int | None = None,
    ) -> Optional[Dict[str, object]]:
        manifest_candidates = self._resolve_candidate_packages(
            persona_id=persona_id,
            intent=intent,
            tone=tone,
            context_tags=context_tags,
        )
        if not manifest_candidates:
            return None

        avoid_set = {aid for aid in avoid_asset_ids or []}
        recent_set = set(recent_asset_ids or [])
        rng = random.Random(seed) if seed is not None else self._rng

        candidates: List[Tuple[float, ClipPayload, EmotionPackageManifest, EmotionIntentConfig]] = []

        for manifest, intent_cfg, package_score in manifest_candidates:
            clips = self._load_clips(manifest.uuid, intent)
            if not clips:
                continue
            intent_weight = intent_cfg.weight or 1.0
            for clip in clips:
                asset_path = self.asset_service.get_asset_path(clip.asset_id)
                if not asset_path:
                    continue
                weight = max(0.01, intent_weight * package_score)
                if clip.confidence is not None:
                    weight *= max(0.1, min(1.0, clip.confidence))
                if clip.duration:
                    weight *= min(1.5, max(0.5, clip.duration / 3.0))
                if clip.motion is not None:
                    weight *= max(0.25, min(1.5, 0.75 + clip.motion))
                meta = clip.analysis_metadata or {}
                expr_conf = meta.get("expression_confidence")
                if expr_conf is not None:
                    try:
                        expr_conf_f = float(expr_conf)
                    except (TypeError, ValueError):
                        expr_conf_f = None
                    if expr_conf_f is not None:
                        weight *= max(0.5, min(1.75, 0.85 + expr_conf_f))
                if clip.asset_id in avoid_set:
                    weight *= 0.1
                if clip.asset_id in recent_set:
                    weight *= 0.2
                if weight <= 0:
                    continue
                candidates.append((weight, clip, manifest, intent_cfg))

        if not candidates:
            return None

        weights = [max(0.001, item[0]) for item in candidates]
        chosen_weight, chosen_clip, chosen_manifest, chosen_cfg = rng.choices(
            candidates, weights=weights, k=1
        )[0]

        selection = self._build_selection_dict(
            clip=chosen_clip,
            manifest=chosen_manifest,
            intent_cfg=chosen_cfg,
        )

        self._record_recent(persona_id, intent, chosen_clip.asset_id)
        return selection

    # ------------------------------------------------------------------
    # Internal helpers

    def _build_selection_dict(
        self,
        *,
        clip: ClipPayload,
        manifest: EmotionPackageManifest,
        intent_cfg: EmotionIntentConfig,
    ) -> Dict[str, object]:
        asset_path = self.asset_service.get_asset_path(clip.asset_id)
        if not asset_path:
            asset_path = str(Path(manifest.path) / clip.rel_path)
        selection = {
            "asset_id": clip.asset_id,
            "package_uuid": manifest.uuid,
            "intent": clip.intent,
            "path": asset_path,
            "rel_path": clip.rel_path,
            "loop_start": clip.loop_start,
            "loop_end": clip.loop_end,
            "duration": clip.duration,
            "confidence": clip.confidence,
            "motion": clip.motion,
            "tags": clip.tags,
            "metadata": clip.analysis_metadata,
            "intent_weight": intent_cfg.weight,
            "package": {
                "name": manifest.name,
                "persona_ids": manifest.persona_ids,
                "context_tags": manifest.context_tags,
                "supported_tones": manifest.supported_tones,
            },
        }
        return selection

    def _resolve_candidate_packages(
        self,
        *,
        persona_id: str | None,
        intent: str,
        tone: str | None,
        context_tags: Iterable[str] | None,
    ) -> List[Tuple[EmotionPackageManifest, EmotionIntentConfig, float]]:
        tone_normalized = tone.lower() if tone else None
        context_set = {tag.lower() for tag in context_tags or []}

        package_ids: List[str] = []
        if persona_id and persona_id in self._persona_index:
            package_ids.extend(self._persona_index.get(persona_id, []))
        package_ids.extend(self._persona_index.get(_SHARED_PERSONA, []))
        seen: set[str] = set()
        results: List[Tuple[EmotionPackageManifest, EmotionIntentConfig, float]] = []

        for package_uuid in package_ids:
            if package_uuid in seen:
                continue
            seen.add(package_uuid)
            manifest = self._packages.get(package_uuid)
            if not manifest:
                continue
            intent_cfg = manifest.intents.get(intent)
            if not intent_cfg:
                continue
            base_score = 1.0
            meta = self._package_meta.get(package_uuid, {})
            tone_match = meta.get("tones", set())
            if tone_normalized and tone_match:
                if tone_normalized in tone_match:
                    base_score += 0.75
                else:
                    base_score *= 0.5
            context_match = meta.get("context", set())
            if context_set:
                overlap = context_match.intersection(context_set)
                if overlap:
                    base_score += 0.25 * len(overlap)
                elif context_match:
                    base_score *= 0.6
            results.append((manifest, intent_cfg, base_score))
        return results

    def _load_clips(self, package_uuid: str, intent: str) -> List[ClipPayload]:
        cache_key = (package_uuid, intent)
        cached = self._clip_cache.get(cache_key)
        if cached is not None:
            return cached
        records = self.repository.list_clips(
            package_uuid=package_uuid,
            intents=[intent],
        )
        payloads = [
            ClipPayload(
                asset_id=record.asset_id,
                package_uuid=record.package_uuid,
                intent=record.intent,
                rel_path=record.rel_path,
                loop_start=record.loop_start,
                loop_end=record.loop_end,
                duration=record.duration,
                motion=record.motion,
                confidence=record.confidence,
                tags=list(record.tags or []),
                analysis_metadata=dict(record.analysis_metadata or {}),
            )
            for record in records
        ]
        self._clip_cache[cache_key] = payloads
        return payloads

    def _record_recent(self, persona_id: str | None, intent: str, asset_id: str) -> None:
        key = (persona_id or _SHARED_PERSONA, intent)
        history = self._recent_history.setdefault(key, [])
        history.append(asset_id)
        if len(history) > 6:
            del history[0 : len(history) - 6]

    # ------------------------------------------------------------------
    # Event hooks

    def _on_packages_synced(self, **_: object) -> None:
        self.refresh_manifests()

    def _on_package_updated(self, package_uuid: str | None = None, **_: object) -> None:
        if package_uuid:
            self.invalidate_package(package_uuid)
        else:
            self.refresh_manifests()



