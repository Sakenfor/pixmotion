
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Iterable

class BaseLayerGenerator:
    """Subclass and implement process_asset(asset_id) to populate tags for a layer."""
    def __init__(self, framework, layer_desc: Dict[str, Any]):
        self.framework = framework
        self.log = framework.log_manager
        self.layer = layer_desc
        self.tag_index = framework.get_service("tag_index_service")
        self.repository = framework.get_service("asset_repository")
        project_root = framework.get_project_root() if framework else None
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def process_asset(self, asset_id: str) -> None:
        raise NotImplementedError
