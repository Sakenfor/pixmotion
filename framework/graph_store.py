from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .graph_schema import GraphDocument, graph_from_dict, graph_to_dict


class GraphStore:
    """In-memory store for scenario graphs and templates with optional persistence."""

    def __init__(self, log_manager):
        self.log = log_manager
        self._graphs: Dict[str, GraphDocument] = {}

    def save(self, graph: GraphDocument) -> None:
        self._graphs[graph.id] = graph
        self.log.info("Graph '%s' saved to store.", graph.id)

    def exists(self, graph_id: str) -> bool:
        return graph_id in self._graphs

    def get(self, graph_id: str) -> Optional[GraphDocument]:
        graph = self._graphs.get(graph_id)
        if not graph:
            return None
        return graph.copy()

    def delete(self, graph_id: str) -> None:
        if graph_id in self._graphs:
            self._graphs.pop(graph_id)
            self.log.info("Graph '%s' removed from store.", graph_id)

    def list_graph_ids(self) -> List[str]:
        return list(self._graphs.keys())

    def clone_graph(self, graph_id: str, *, new_id: str) -> Optional[GraphDocument]:
        graph = self._graphs.get(graph_id)
        if not graph:
            return None
        clone = graph.copy(new_id=new_id)
        self._graphs[new_id] = clone
        self.log.info("Graph '%s' cloned as '%s'.", graph_id, new_id)
        return clone

    def iter_graphs(self) -> Iterable[GraphDocument]:
        for graph in self._graphs.values():
            yield graph.copy()

    def clear(self) -> None:
        self._graphs.clear()

    # --- Persistence -------------------------------------------------

    def load_from_directory(self, directory: str) -> None:
        base_path = Path(directory)
        if not base_path.exists():
            self.log.info("Graph directory '%s' does not exist. Nothing to load.", directory)
            return

        for file_path in base_path.glob('*.graph.json'):
            try:
                graph = self._load_file(file_path)
            except Exception as exc:  # noqa: BLE001
                self.log.error("Failed to load graph file %s: %s", file_path, exc, exc_info=True)
                continue

            self._graphs[graph.id] = graph
            self.log.info("Graph '%s' loaded from '%s'.", graph.id, file_path)

    def save_to_directory(self, directory: str) -> None:
        base_path = Path(directory)
        base_path.mkdir(parents=True, exist_ok=True)

        for graph in self._graphs.values():
            file_path = base_path / f"{graph.id}.graph.json"
            try:
                self._write_file(file_path, graph)
            except Exception as exc:  # noqa: BLE001
                self.log.error("Failed to write graph '%s' to '%s': %s", graph.id, file_path, exc, exc_info=True)

    def _load_file(self, file_path: Path) -> GraphDocument:
        data = json.loads(file_path.read_text(encoding='utf-8'))
        return graph_from_dict(data)

    def _write_file(self, file_path: Path, graph: GraphDocument) -> None:
        payload = graph_to_dict(graph)
        file_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
