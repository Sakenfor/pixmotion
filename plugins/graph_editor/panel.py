from __future__ import annotations

"""Canonical implementation of the graph editor dock panel.

This module is intentionally the single home for ``GraphExplorerPanel`` so the
plugin entry point and any future helpers can import it without ambiguity.
The panel owns all UI handlers for editing graphs, including drag-and-drop
asset management and metadata inspection.
"""

import math
from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QSplitter, \
    QGraphicsScene, QLabel, QTreeWidget, QTreeWidgetItem, QCheckBox, QMessageBox, QDialog

from framework.graph_schema import GraphDocument, GraphNode, GraphEdge, graph_from_dict, graph_to_dict
from .graph_view import _NodeGraphicsView
from .graph_nodes import _GraphNodeItem, _Socket
from .graph_edges import _GraphEdgeItem
from .graph_dialogs import GraphCreateDialog, NodeCreateDialog, EdgeCreateDialog, EdgeManageDialog, DeleteNodeDialog


REQUIRED_METADATA_KEYS: Tuple[str, ...] = ("persona_hint", "descriptor")


class GraphExplorerPanel(QWidget):
    """Dockable panel providing a Blender-like node editor.

    Besides the node-graph manipulation affordances, the panel centralises
    asset drop handling and basic metadata validation so the dock presents a
    consistent authoring workflow.
    """

    def __init__(self, framework):
        super().__init__()
        self.framework = framework
        self.log = framework.log_manager
        self.graph_service = framework.graph_service
        self.graph_registry = framework.graph_registry

        self._current_graph_id: Optional[str] = None
        self._current_graph: Optional[GraphDocument] = None
        self._graph_dirty: bool = False
        self._node_items: Dict[str, _GraphNodeItem] = {}
        self._edge_items: Dict[int, _GraphEdgeItem] = {}

        self._build_ui()
        self._refresh_graphs()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        tb = QHBoxLayout()
        tb.addWidget(QPushButton("Refresh", clicked=self._refresh_graphs))
        tb.addWidget(QPushButton("New Graph", clicked=self._prompt_new_graph))
        tb.addWidget(QPushButton("Add Node", clicked=self._prompt_new_node))
        tb.addWidget(QPushButton("Save", clicked=self._save_graph))
        self._snap_checkbox = QCheckBox("Snap")
        self._snap_checkbox.setChecked(True)
        self._snap_checkbox.toggled.connect(self._on_toggle_snap)
        tb.addWidget(self._snap_checkbox)
        tb.addStretch(1)
        self._summary_label = QLabel("No graphs loaded")
        tb.addWidget(self._summary_label)
        root.addLayout(tb)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        self._graph_list = QListWidget(splitter)
        self._graph_list.itemSelectionChanged.connect(self._handle_graph_selection)
        splitter.addWidget(self._graph_list)

        container = QWidget(splitter)
        container.panel = self
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        self._scene = QGraphicsScene(self)
        self._view = _NodeGraphicsView(self._scene, container)
        layout.addWidget(self._view)
        splitter.addWidget(container)

        self._detail_tree = QTreeWidget()
        self._detail_tree.setColumnCount(2)
        self._detail_tree.setHeaderLabels(["Field", "Value"])
        splitter.addWidget(self._detail_tree)

        splitter.setSizes([240, 800, 360])

        self._view.request_add_node.connect(self._add_node_at_pos)
        self._view.request_delete_selection.connect(self._delete_selection)
        self._view.edge_dropped.connect(self._on_edge_dropped)
        self._view.edge_rewired.connect(self._on_edge_rewired)
        self._view.asset_dropped_on_node.connect(self._on_asset_dropped)

    def _on_asset_dropped(self, asset_id: str, node_id: str):
        """Attach the dropped asset to the target node and refresh details."""

        if not self._ensure_graph_loaded():
            return

        node = self._current_graph.get_node(node_id)
        if not node:
            self.log.error(f"Could not find node '{node_id}' to drop asset on.")
            return

        if asset_id not in node.asset_refs:
            node.asset_refs.append(asset_id)
            self.log.info(f"Asset '{asset_id}' added to node '{node_id}'.")
            self._mark_dirty(True)
            if self._detail_tree.topLevelItem(0) and self._detail_tree.topLevelItem(0).text(1) == node_id:
                self._show_node_details(node)
        else:
            self.log.info(f"Asset '{asset_id}' is already on node '{node_id}'.")

    def _on_edge_dropped(self, source_socket: _Socket, target_socket: Optional[_Socket]):
        if not self._ensure_graph_loaded() or not target_socket or source_socket == target_socket:
            return

        if source_socket.is_output == target_socket.is_output:
            self.log.warning("Cannot connect sockets of the same type (output to output or input to input).")
            return

        source_node = source_socket.parent_node
        target_node = target_socket.parent_node
        if source_node == target_node:
            self.log.warning("Cannot connect a node to itself.")
            return

        source_id = source_node.node.id if source_socket.is_output else target_node.node.id
        target_id = target_node.node.id if source_socket.is_output else source_node.node.id

        if any(e.source == source_id and e.target == target_id for e in self._current_graph.edges):
            self.log.info("An edge between these nodes already exists.")
            return

        self._create_edge(source_id, target_id, "link")

    def _on_edge_rewired(self, edge_item: _GraphEdgeItem, is_source: bool, target_socket: Optional[_Socket]):
        if not self._ensure_graph_loaded() or not target_socket:
            return

        original_edge = self._current_graph.edges[edge_item.index]
        target_node_id = target_socket.parent_node.node.id

        if is_source:
            if not target_socket.is_output:
                self.log.warning("The source of an edge must connect to an OUTPUT socket.")
                return
            if target_node_id == original_edge.target:
                self.log.warning("Cannot connect a node to itself.")
                return
            original_edge.source = target_node_id
        else:  # is target
            if target_socket.is_output:
                self.log.warning("The target of an edge must connect to an INPUT socket.")
                return
            if target_node_id == original_edge.source:
                self.log.warning("Cannot connect a node to itself.")
                return
            original_edge.target = target_node_id

        self._render_graph(self._current_graph)
        self._select_edge_in_scene(edge_item.index)
        self._mark_dirty(True)

    def _on_node_moved(self, item: _GraphNodeItem):
        self._save_node_pos(item.node.id, item.pos())
        self._mark_dirty(True)

    def _on_toggle_snap(self, enabled: bool) -> None:
        self._view.set_snap_enabled(enabled)

    def save_state(self) -> Dict[str, str]:
        return {"selected_graph": self._current_graph_id or ""}

    def restore_state(self, state: Dict[str, str]) -> None:
        if isinstance(state, dict):
            if gid := state.get("selected_graph"):
                self._select_graph_by_id(gid)

    def _prompt_new_graph(self):
        existing_ids = {info["id"] for info in self.graph_service.list_graphs()}
        dialog = GraphCreateDialog(self, existing_ids=existing_ids)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            graph_id, title = dialog.result()
            try:
                graph = GraphDocument(id=graph_id, metadata={"name": title} if title else {})
                self.graph_service.save_graph(graph_to_dict(graph), persist=True)
                self._refresh_graphs()
                self._select_graph_by_id(graph_id)
            except Exception as exc:
                QMessageBox.critical(self, "New Graph", f"Failed to create graph: {exc}")

    def _refresh_graphs(self):
        self._graph_list.clear()
        graphs = self.graph_service.list_graphs()
        if not graphs:
            self._summary_label.setText("No graphs available")
            self._current_graph = self._current_graph_id = None
            self._scene.clear()
            self._detail_tree.clear()
            return
        for info in graphs:
            item = QListWidgetItem(f"{info['id']} ({info['node_count']} nodes)")
            item.setData(Qt.ItemDataRole.UserRole, info["id"])
            self._graph_list.addItem(item)
        self._summary_label.setText(f"Loaded {len(graphs)} graph(s)")
        if self._graph_list.count() > 0:
            self._graph_list.setCurrentRow(0)
        self._mark_dirty(False)

    def _handle_graph_selection(self):
        if items := self._graph_list.selectedItems():
            self._load_graph(items[0].data(Qt.ItemDataRole.UserRole))

    def _select_graph_by_id(self, graph_id: str):
        for i in range(self._graph_list.count()):
            it = self._graph_list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == graph_id:
                self._graph_list.setCurrentItem(it)
                return

    def _load_graph(self, graph_id: str):
        if self._graph_dirty:
            reply = QMessageBox.question(self, "Unsaved Changes", "You have unsaved changes. Discard them?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self._select_graph_by_id(self._current_graph_id)
                return

        if payload := self.graph_service.get_graph(graph_id):
            self._current_graph = graph_from_dict(payload)
            self._current_graph_id = graph_id
            self._render_graph(self._current_graph)
            self._mark_dirty(False)
        else:
            self.log.warning(f"Graph '{graph_id}' could not be loaded.")

    def _save_graph(self):
        if not self._ensure_graph_loaded(): return
        try:
            self.graph_service.save_graph(graph_to_dict(self._current_graph), persist=True)
            self._mark_dirty(False)
            QMessageBox.information(self, "Save Graph", "Graph saved successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Graph", f"Failed to save graph: {exc}")

    def _mark_dirty(self, dirty: bool = True):
        self._graph_dirty = dirty
        if not self._current_graph_id or not self._current_graph: return
        suffix = " *" if self._graph_dirty else ""
        self._summary_label.setText(
            f"'{self._current_graph_id}' -> {len(self._current_graph.nodes)} nodes / {len(self._current_graph.edges)} edges{suffix}"
        )

    def _ensure_graph_loaded(self) -> bool:
        if self._current_graph is None:
            QMessageBox.information(self, "Graph Editor", "Select or create a graph first.")
            return False
        return True

    def _prompt_new_node(self):
        if not self._ensure_graph_loaded(): return
        types = sorted(self.graph_registry.node_types.keys()) if self.graph_registry else ["generic"]
        dialog = NodeCreateDialog(self, types, {n.id for n in self._current_graph.nodes})
        if dialog.exec() == QDialog.DialogCode.Accepted:
            node_id, node_type, label = dialog.result()
            new_node = GraphNode(id=node_id, type=node_type, label=label)
            self._current_graph.nodes.append(new_node)
            pos = list(self._auto_layout_positions(self._current_graph).values())[-1]
            self._current_graph.layout.setdefault("nodes", {})[node_id] = {"x": pos.x(), "y": pos.y()}
            self._add_node_item_to_scene(new_node)
            self._select_node_in_scene(node_id)
            self._mark_dirty(True)

    def _add_node_at_pos(self, pos: QPointF):
        self._prompt_new_node()
        if sel_id := next((item.node.id for item in self._scene.selectedItems() if isinstance(item, _GraphNodeItem)),
                          None):
            if item := self._node_items.get(sel_id):
                item.setPos(self._view.snap_point(pos))

    def _create_edge(self, source_id: str, target_id: str, relation: str):
        if not self._ensure_graph_loaded(): return
        new_edge = GraphEdge(source=source_id, target=target_id, relation_type=relation)
        index = len(self._current_graph.edges)
        self._current_graph.edges.append(new_edge)
        self._add_edge_item_to_scene(new_edge, index)
        self._select_edge_in_scene(index)
        self._mark_dirty(True)

    def _delete_selection(self):
        if not self._ensure_graph_loaded(): return
        to_delete_nodes = {item.node.id for item in self._scene.selectedItems() if isinstance(item, _GraphNodeItem)}
        to_delete_edges = {item.index for item in self._scene.selectedItems() if isinstance(item, _GraphEdgeItem)}

        if not to_delete_nodes and not to_delete_edges: return

        edge_indices_to_remove = set(to_delete_edges)
        for i, edge in enumerate(self._current_graph.edges):
            if edge.source in to_delete_nodes or edge.target in to_delete_nodes:
                edge_indices_to_remove.add(i)

        for idx in sorted(edge_indices_to_remove, reverse=True):
            self._current_graph.edges.pop(idx)

        self._current_graph.nodes = [n for n in self._current_graph.nodes if n.id not in to_delete_nodes]
        for nid in to_delete_nodes:
            self._current_graph.layout.get("nodes", {}).pop(nid, None)

        self._render_graph(self._current_graph)
        self._mark_dirty(True)

    def _save_node_pos(self, node_id: str, pos: QPointF):
        if self._current_graph:
            entry = self._current_graph.layout.setdefault("nodes", {}).setdefault(node_id, {})
            entry["x"], entry["y"] = pos.x(), pos.y()

    def _save_node_socket_counts(self, node_id: str, inputs: int, outputs: int):
        if self._current_graph:
            entry = self._current_graph.layout.setdefault("nodes", {}).setdefault(node_id, {})
            entry["inputs"], entry["outputs"] = int(inputs), int(outputs)

    def _get_node_layout_cfg(self, node_id: str) -> dict:
        return self._current_graph.layout.get("nodes", {}).get(node_id, {}) if self._current_graph else {}

    def _auto_layout_positions(self, graph: GraphDocument) -> Dict[str, QPointF]:
        positions = {}
        n = max(1, len(graph.nodes))
        radius = max(240, n * 40)
        for i, node in enumerate(graph.nodes):
            angle = (2 * math.pi * i) / n
            positions[node.id] = QPointF(math.cos(angle) * radius, math.sin(angle) * radius)
        return positions

    def _add_node_item_to_scene(self, node: GraphNode):
        cfg = self._get_node_layout_cfg(node.id)
        pos = QPointF(float(cfg.get("x", 0.0)), float(cfg.get("y", 0.0)))
        item = _GraphNodeItem(self, node, pos)
        self._scene.addItem(item)
        self._node_items[node.id] = item
        return item

    def _add_edge_item_to_scene(self, edge: GraphEdge, index: int):
        src_node = self._node_items.get(edge.source)
        tgt_node = self._node_items.get(edge.target)
        if src_node and tgt_node:
            item = _GraphEdgeItem(index, edge.source, edge.target, edge.relation_type)
            self._edge_items[index] = item
            item.set_node_items(src_node, tgt_node)
            item.update_positions()
            self._scene.addItem(item)
            return item
        return None

    def _render_graph(self, graph: GraphDocument):
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()

        if not graph.layout.get("nodes"):
            graph.layout["nodes"] = {nid: {"x": p.x(), "y": p.y()} for nid, p in
                                     self._auto_layout_positions(graph).items()}

        for node in graph.nodes:
            self._add_node_item_to_scene(node)

        for idx, edge in enumerate(graph.edges):
            self._add_edge_item_to_scene(edge, idx)

        self._detail_tree.clear()
        if self._scene.items():
            self._view.fitInView(self._scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _select_node_in_scene(self, node_id: str):
        if item := self._node_items.get(node_id):
            self._scene.clearSelection()
            item.setSelected(True)
            self._view.ensureVisible(item)
            self._show_node_details(item.node)

    def _select_edge_in_scene(self, edge_index: int):
        if item := self._edge_items.get(edge_index):
            self._scene.clearSelection()
            item.setSelected(True)
            self._view.ensureVisible(item)
            self._show_edge_details(self._current_graph.edges[edge_index])

    def _show_node_details(self, node: GraphNode):
        self._detail_tree.clear()
        self._detail_tree.setUpdatesEnabled(False)  # Performance improvement

        QTreeWidgetItem(self._detail_tree, ["ID", node.id])
        QTreeWidgetItem(self._detail_tree, ["Type", node.type])
        QTreeWidgetItem(self._detail_tree, ["Label", node.label or "<none>"])

        assets_parent = QTreeWidgetItem(self._detail_tree, ["Asset Refs", f"({len(node.asset_refs)})"])
        for ref in node.asset_refs:
            QTreeWidgetItem(assets_parent, [ref])
        assets_parent.setExpanded(True)

        metadata_parent = QTreeWidgetItem(self._detail_tree, ["Metadata", ""])
        if node.metadata:
            for key, value in sorted(node.metadata.items()):
                QTreeWidgetItem(metadata_parent, [key, str(value)])
        else:
            QTreeWidgetItem(metadata_parent, ["<none>", ""])

        missing_keys = [key for key in REQUIRED_METADATA_KEYS if key not in node.metadata]
        if missing_keys:
            QTreeWidgetItem(metadata_parent, ["Missing required", ", ".join(missing_keys)])
        metadata_parent.setExpanded(True)

        self._detail_tree.setUpdatesEnabled(True)
        self._detail_tree.resizeColumnToContents(0)

    def _show_edge_details(self, edge: GraphEdge):
        self._detail_tree.clear()
        QTreeWidgetItem(self._detail_tree, ["Source", edge.source])
        QTreeWidgetItem(self._detail_tree, ["Target", edge.target])
        QTreeWidgetItem(self._detail_tree, ["Relation", edge.relation_type])
        self._detail_tree.resizeColumnToContents(0)

