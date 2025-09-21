from __future__ import annotations

from typing import Dict, Optional, Sequence, Set

from sqlalchemy.orm import Session

from .models import EmotionClip


class EmotionClipRepository:
    """Persisted analytics for emotion loop clips."""

    def __init__(self, framework):
        self._db = framework.get_service("database_service")
        self._log = framework.get_service("log_manager")

    def upsert_clip(
        self,
        *,
        asset_id: str,
        package_uuid: str,
        intent: str,
        rel_path: str,
        loop_start: float | None = None,
        loop_end: float | None = None,
        duration: float | None = None,
        motion: float | None = None,
        confidence: float | None = None,
        tags: Sequence[str] | None = None,
        embedding: Sequence[float] | None = None,
        analysis_metadata: Dict[str, object] | None = None,
    ) -> EmotionClip | None:
        session: Session = self._db.get_session()
        try:
            clip = (
                session.query(EmotionClip)
                .filter_by(asset_id=asset_id, package_uuid=package_uuid, intent=intent)
                .one_or_none()
            )
            if clip is None:
                clip = EmotionClip(
                    asset_id=asset_id,
                    package_uuid=package_uuid,
                    intent=intent,
                    rel_path=rel_path,
                    loop_start=loop_start,
                    loop_end=loop_end,
                    duration=duration,
                    motion=motion,
                    confidence=confidence,
                    tags=list(tags) if tags else None,
                    embedding=list(embedding) if embedding else None,
                    analysis_metadata=dict(analysis_metadata) if analysis_metadata else None,
                )
                session.add(clip)
            else:
                clip.rel_path = rel_path
                clip.loop_start = loop_start
                clip.loop_end = loop_end
                clip.duration = duration
                clip.motion = motion
                clip.confidence = confidence
                clip.tags = list(tags) if tags else None
                clip.embedding = list(embedding) if embedding else None
                clip.analysis_metadata = dict(analysis_metadata) if analysis_metadata else None
            session.commit()
            return clip
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            self._log.error(
                "Failed to upsert emotion clip for %s (%s/%s): %s",
                asset_id,
                package_uuid,
                intent,
                exc,
                exc_info=True,
            )
            return None
        finally:
            session.close()

    def remove_missing(
        self,
        *,
        package_uuid: str,
        intent: str,
        keep_asset_ids: Set[str],
    ) -> int:
        session: Session = self._db.get_session()
        removed = 0
        try:
            query = session.query(EmotionClip).filter_by(
                package_uuid=package_uuid,
                intent=intent,
            )
            for clip in query.all():
                if clip.asset_id not in keep_asset_ids:
                    session.delete(clip)
                    removed += 1
            if removed:
                session.commit()
            else:
                session.rollback()
            return removed
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            self._log.error(
                "Failed to remove obsolete clips for package %s intent %s: %s",
                package_uuid,
                intent,
                exc,
                exc_info=True,
            )
            return 0
        finally:
            session.close()

    def list_clips(
        self,
        *,
        package_uuid: str | None = None,
        package_uuids: Sequence[str] | None = None,
        intents: Sequence[str] | None = None,
    ) -> list[EmotionClip]:
        session: Session = self._db.get_session()
        try:
            query = session.query(EmotionClip)
            if package_uuid:
                query = query.filter(EmotionClip.package_uuid == package_uuid)
            elif package_uuids:
                query = query.filter(EmotionClip.package_uuid.in_(list(package_uuids)))
            if intents:
                query = query.filter(EmotionClip.intent.in_(list(intents)))
            return (
                query
                .order_by(EmotionClip.package_uuid, EmotionClip.intent, EmotionClip.asset_id)
                .all()
            )
        finally:
            session.close()

    def list_clips_for_package(self, package_uuid: str) -> list[EmotionClip]:
        return self.list_clips(package_uuid=package_uuid)

