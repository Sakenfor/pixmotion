
from __future__ import annotations
from .base_generator import BaseLayerGenerator

class AIDeepGenerator(BaseLayerGenerator):
    """Placeholder for deep model. For now, map ai_quick->coarse emotion guess."""
    def process_asset(self, asset_id: str) -> None:
        layers = self.tag_index.get_layers_for_asset(asset_id)
        quick = set(layers.get("ai_quick",{}).get("tags",[]))
        tags = set()
        if "portrait" in quick:
            tags.add("emotion:happy")  # stub
        self.tag_index.add_tags(asset_id, "ai_deep", tags or {"needs_review"})
