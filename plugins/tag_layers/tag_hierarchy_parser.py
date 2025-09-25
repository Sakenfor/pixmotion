from typing import Any, Dict, List, Optional, Set

class TagHierarchyParser:
    def __init__(self, hierarchy_data: Dict[str, Any]):
        self._hierarchy = hierarchy_data
        self._parent_map: Dict[str, str] = {}
        self._all_tags: Set[str] = set()
        self._build_maps(self._hierarchy)

    def _build_maps(self, node: Dict[str, Any], parent: Optional[str] = None):
        for key, value in node.items():
            self._all_tags.add(key)
            if parent: self._parent_map[key] = parent
            if isinstance(value, dict): self._build_maps(value, key)

    def get_ancestors(self, tag: str) -> List[str]:
        ancestors = []
        current = self._parent_map.get(tag)
        while current:
            ancestors.append(current)
            current = self._parent_map.get(current)
        return ancestors

    def get_descendants(self, tag: str) -> List[str]:
        descendants = set()
        def find_children(node: Dict[str, Any]):
            for key, value in node.items():
                descendants.add(key)
                if isinstance(value, dict): find_children(value)
        start_node = self._find_node(self._hierarchy, tag)
        if isinstance(start_node, dict): find_children(start_node)
        descendants.discard(tag)
        return sorted(list(descendants))

    def _find_node(self, node: Dict[str, Any], target_tag: str) -> Optional[Dict[str, Any]]:
        if target_tag in node: return node[target_tag]
        for value in node.values():
            if isinstance(value, dict):
                found = self._find_node(value, target_tag)
                if found is not None: return found
        return None
