
from __future__ import annotations
import os
from .base_generator import BaseLayerGenerator

class AIQuickGenerator(BaseLayerGenerator):
    """Cheap heuristic 'AI quick' generator (filename & extension based)."""
    def process_asset(self, asset_id: str) -> None:
        path = None
        if self.repository:
            path = self.repository.get_path_by_id(asset_id)
        tags = set()
        if path:
            lower = os.path.basename(path).lower()
            if any(x in lower for x in ("portrait", "headshot", "face")):
                tags.add("portrait")
            if any(x in lower for x in ("dog","cat","pet")):
                tags.add("animal")
            ext = os.path.splitext(lower)[1]
            if ext in (".mp4",".mov",".avi",".mkv"):
                tags.add("video")
            else:
                tags.add("image")
        # Fallback minimal tagging
        if not tags:
            tags.add("unknown")
        self.tag_index.add_tags(asset_id, "ai_quick", tags)
