# Graph Editor Roadmap

## Current State
- Graph Explorer dock lists graphs, creates new ones, and saves changes via GraphService.
- Canvas renders nodes/edges with selection highlighting; node inspector allows editing type, label, tags, properties (JSON), metadata (JSON).
- Edge manager dialog renames or deletes edges; double-clicking an edge opens the dialog.
- Toolbar actions: Refresh, New Graph, Add Node, Add Edge, Edit Edge, Delete Node, Save.

## Immediate Next Steps
1. **Node Properties UI**
   - Replace raw JSON editors with structured inputs for common fields (e.g., key-value table, tag chips).
   - Add validation feedback for required node metadata (persona hints, descriptors).
2. **Edge Context Actions**
   - Add right-click menu for edges with quick rename/delete.
   - Display relation info in overlay near selected edge.
3. **Canvas Interaction Polish**
   - Enable drag-to-reposition nodes and persist layout (write layout back to graph metadata).
   - Implement multi-select (shift+click) to support batch deletes.
4. **Node Actions Editor**
   - Visual editor for ctions list (add/remove action variants, priorities, cooldowns).
   - Integrate qualitative scale picker for conditions.

## Medium-Term Goals
- Undo/redo stack scoped to graph editing session.
- Autosave with dirty markers per graph.
- Filter/search panel for nodes by tag, type, relation.
- Snap-to-grid layout and automated graph layout options (hierarchical/circular).

## Longer-Term Vision
- Inline asset previews (thumbnails for asset_refs).
- Scriptable node behaviors via prompt snippets, integrated with orchestrator personas.
- Collaborative editing (merge conflicts, change tracking).
- Testing harness: simulate orchestrator passes on the current graph and show outcomes in the UI.

