from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .graph_schema import GraphDocument, graph_from_dict, graph_to_dict


class GraphService:
    """High-level facade over the graph registry and store for editor tooling."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.log_manager
        self.store = framework.graph_store
        self.registry = framework.graph_registry
        self._data_directory: Optional[Path] = None
        self._settings_service = None

    # --- Data directory -------------------------------------------------

    def set_data_directory(self, path: str) -> None:
        self._data_directory = Path(path)

    def get_data_directory(self) -> Path:
        if self._data_directory is not None:
            return self._data_directory

        settings = self._get_settings_service()
        if settings:
            directory = Path(settings.resolve_user_path("graphs"))
            self._data_directory = directory
            return directory

        project_root = getattr(self.framework, "project_root", None)
        if project_root:
            directory = Path(project_root) / "graphs"
            directory.mkdir(parents=True, exist_ok=True)
            return directory
        return Path("graphs")

    def _get_settings_service(self):
        if self._settings_service is None:
            getter = getattr(self.framework, "get_service", None)
            if callable(getter):
                self._settings_service = getter("settings_service")
        return self._settings_service

    # --- Persistence ----------------------------------------------------

    def load_all(self) -> None:
        directory = self.get_data_directory()
        self.store.load_from_directory(str(directory))

    def save_all(self) -> None:
        directory = self.get_data_directory()
        self.store.save_to_directory(str(directory))

    # --- Graph CRUD -----------------------------------------------------

    def list_graphs(self) -> List[Dict[str, Any]]:
        graphs: List[Dict[str, Any]] = []
        for graph in self.store.iter_graphs():
            graphs.append(
                {
                    "id": graph.id,
                    "metadata": graph.metadata,
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                }
            )
        return graphs

    def get_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        graph = self.store.get(graph_id)
        if not graph:
            return None
        return graph_to_dict(graph)

    def save_graph(self, data: Dict[str, Any], *, persist: bool = False) -> Dict[str, Any]:
        graph = graph_from_dict(data)
        self.store.save(graph)
        if persist:
            self.save_all()
        return graph_to_dict(graph)

    def delete_graph(self, graph_id: str, *, persist: bool = False) -> bool:
        if not self.store.exists(graph_id):
            return False
        self.store.delete(graph_id)
        if persist:
            self.save_all()
        return True

    def clone_graph(self, source_id: str, new_id: str, *, persist: bool = False) -> Optional[Dict[str, Any]]:
        graph = self.store.clone_graph(source_id, new_id=new_id)
        if not graph:
            return None
        if persist:
            self.save_all()
        return graph_to_dict(graph)

    def import_graph(self, file_path: str, *, persist: bool = False) -> Dict[str, Any]:
        path = Path(file_path)
        payload = json.loads(path.read_text(encoding='utf-8'))
        graph = graph_from_dict(payload)
        self.store.save(graph)
        if persist:
            self.save_all()
        return graph_to_dict(graph)

    def export_graph(self, graph_id: str, file_path: str) -> bool:
        graph = self.store.get(graph_id)
        if not graph:
            return False
        payload = graph_to_dict(graph)
        Path(file_path).write_text(json.dumps(payload, indent=2), encoding='utf-8')
        return True
