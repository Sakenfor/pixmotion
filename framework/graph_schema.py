from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(slots=True)
class ActionVariant:
    """Represents an individual media clip or script inside an action."""

    asset: str
    weight: float = 1.0
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NodeAction:
    """A reusable action the orchestrator can trigger on a node."""

    id: str
    mode: str = "one_shot"  # loop | sequence | playlist
    variants: List[ActionVariant] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    cooldown: Optional[str] = None
    priority: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphNode:
    """A typed node within a scenario graph."""

    id: str
    type: str
    label: str = ""
    tags: List[str] = field(default_factory=list)
    asset_refs: List[str] = field(default_factory=list)
    asset_groups: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    actions: List[NodeAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphEdge:
    """A relation between two nodes."""

    source: str
    target: str
    relation_type: str
    direction: str = "directed"
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None


@dataclass(slots=True)
class PlaceholderDefinition:
    """Describes a slot that must be filled when instantiating a template."""

    id: str
    expected_types: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphDocument:
    """Serializable container for nodes, edges, and supporting metadata."""

    id: str
    version: str = "1.0"
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    placeholders: Dict[str, PlaceholderDefinition] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_edges_from(self, node_id: str, *, relation_type: Optional[str] = None) -> List[GraphEdge]:
        results: List[GraphEdge] = []
        for edge in self.edges:
            if edge.source != node_id:
                continue
            if relation_type and edge.relation_type != relation_type:
                continue
            results.append(edge)
        return results

    def get_edges_to(self, node_id: str, *, relation_type: Optional[str] = None) -> List[GraphEdge]:
        results: List[GraphEdge] = []
        for edge in self.edges:
            if edge.target != node_id:
                continue
            if relation_type and edge.relation_type != relation_type:
                continue
            results.append(edge)
        return results

    def copy(self, *, new_id: Optional[str] = None) -> "GraphDocument":
        import copy

        clone = copy.deepcopy(self)
        if new_id:
            clone.id = new_id
        return clone


# --- Serialisation helpers -------------------------------------------------


def _normalize_list(values) -> List[Any]:
    if not values:
        return []
    if isinstance(values, list):
        return list(values)
    if isinstance(values, tuple):
        return list(values)
    return [values]

def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _build_action(data: Dict[str, Any]) -> NodeAction:
    variants = [
        ActionVariant(
            asset=str(variant.get("asset", "")),
            weight=_to_float(variant.get("weight", 1.0), 1.0),
            tags=_normalize_list(variant.get("tags", [])),
            properties=dict(variant.get("properties", {})),
        )
        for variant in data.get("variants", [])
    ]

    return NodeAction(
        id=str(data["id"]),
        mode=str(data.get("mode", "one_shot")),
        variants=variants,
        steps=[dict(step) for step in data.get("steps", [])],
        conditions=dict(data.get("conditions", {})),
        cooldown=data.get("cooldown"),
        priority=_to_float(data.get("priority", 0.0), 0.0),
        metadata=dict(data.get("metadata", {})),
    )


def _build_node(data: Dict[str, Any]) -> GraphNode:
    return GraphNode(
        id=str(data["id"]),
        type=str(data["type"]),
        label=str(data.get("label", "")),
        tags=[str(tag) for tag in _normalize_list(data.get("tags", []))],
        asset_refs=[str(ref) for ref in _normalize_list(data.get("asset_refs", []))],
        asset_groups=[str(ref) for ref in _normalize_list(data.get("asset_groups", []))],
        properties=dict(data.get("properties", {})),
        actions=[_build_action(action) for action in data.get("actions", [])],
        metadata=dict(data.get("metadata", {})),
    )


def _build_edge(data: Dict[str, Any]) -> GraphEdge:
    return GraphEdge(
        id=data.get("id"),
        source=str(data["source"]),
        target=str(data["target"]),
        relation_type=str(data["relation_type"]),
        direction=str(data.get("direction", "directed")),
        properties=dict(data.get("properties", {})),
        metadata=dict(data.get("metadata", {})),
    )


def _build_placeholder(placeholder_id: str, data: Dict[str, Any]) -> PlaceholderDefinition:
    return PlaceholderDefinition(
        id=str(data.get("id", placeholder_id)),
        expected_types=[str(value) for value in _normalize_list(data.get("expected_types", []))],
        description=str(data.get("description", "")),
        metadata=dict(data.get("metadata", {})),
    )


def graph_from_dict(data: Dict[str, Any]) -> GraphDocument:
    placeholders_data = data.get("placeholders", {})
    placeholders = {
        key: _build_placeholder(key, value)
        for key, value in placeholders_data.items()
    }

    return GraphDocument(
        id=str(data["id"]),
        version=str(data.get("version", "1.0")),
        nodes=[_build_node(node) for node in data.get("nodes", [])],
        edges=[_build_edge(edge) for edge in data.get("edges", [])],
        layout=dict(data.get("layout", {})),
        placeholders=placeholders,
        metadata=dict(data.get("metadata", {})),
    )


def graph_to_dict(graph: GraphDocument) -> Dict[str, Any]:
    return {
        "id": graph.id,
        "version": graph.version,
        "nodes": [asdict(node) for node in graph.nodes],
        "edges": [asdict(edge) for edge in graph.edges],
        "layout": graph.layout,
        "placeholders": {key: asdict(value) for key, value in graph.placeholders.items()},
        "metadata": graph.metadata,
    }


def as_dict(items: Iterable[Any]) -> List[Dict[str, Any]]:
    """Utility to convert dataclass instances to dictionaries for serialization."""

    serialised: List[Dict[str, Any]] = []
    for item in items:
        if is_dataclass(item):
            serialised.append(asdict(item))
        else:
            serialised.append(dict(item))
    return serialised

