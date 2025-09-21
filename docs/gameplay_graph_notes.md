# Gameplay Graph & Orchestrator Notes

- **Vision**: Graph-driven game engine where nodes are fixed at runtime and assets flow like oil through gears. Orchestrator AI walks the graph each in-game day to surface scenes, jobs, and events for the player.
- **Node Categories**: Core base types (`Person`, `Location`, `Activity`, `Event`, `AssetPool`, `StateTrigger`) plus flagged core gear instances (e.g., `PlayerHome`, `NPCResidence`, `Workplace`) that act as anchors. Edges are directed and carry semantic descriptors (`lives_at`, `hosts`, `uses`, etc.).
- **Plugins & Extensibility**: Plugins or creators can extend any base category with new node types. Custom nodes choose a base category, attach metadata/tags/descriptors, and have optional sandboxed scripts or natural language prompts to inform the orchestrator.
- **Assets as Oil**:
  - Assets stay separate from nodes and are selected dynamically; no graph mutation mid-run.
  - Each asset exposes rich tags (persona, outfit, mood, weather fit, etc.) and time-sliced cues (`cue=fall`, `start=3.0s`).
  - Transition metadata links compatible clip segments (`calm outro` -> `eager intro`) so the orchestrator can string pathways together.
  - Later we can support creator-authored clip bundles either in the asset manager or directly in the graph editor.
- **Outcome Pools**: Nodes reference outcome bundles (`ShiftStart`, `SurpriseGuest`, etc.) that map to asset pools plus lightweight selection rules. Keeps graphs lean while allowing variety.
- **Runtime State Layer**: Relationships, stats, timers, and MC personality live outside the graph in a mutable state store keyed by node IDs. Orchestrator reads state to weight choices but node definitions remain static once play begins.
- **MC & NPC Dynamics**: People nodes carry traits; edges track rapport/trust/etc. MC personality presets bias orchestrator choices (e.g., Stoic vs. Chaotic). Presets/versions capture different graph snapshots for alternative campaigns.
- **Orchestrator Personas**:
  - Supports global or scoped personas (`CozySliceOfLife`, `DarkAlleyNarrator`).
  - Personas expose sliders (risk_bias, mystery_level, asset_mood_filter) to adjust difficulty/tone.
  - Can swap personas based on triggers (entering an alley, story beat, etc.).
- **Daily Sweep Ideas**: Morning context pass (weather/festival), node agenda merging, tension/surprise balancing, relationship resonance, resource freshness checks, narrative thread progression.
- **Live Editing**: Custom nodes can be hot-reloaded during development; orchestrator re-evaluates on the next cycle. Scripts remain sandboxed to prevent graph mutation.
- **Open Questions**:
  - Exact format for custom script/prompt interface.
  - Best place to author clip bundles (asset manager vs graph editor).
  - Versioning strategy for presets and runtime personas.


- **Story Arcs & Custom Stats**: Support creator-authored arcs that chain multiple nodes with relationship/stats gating. Allow users to define bespoke stat tracks, attach rules for how scenes modify them, and let orchestrator use stat thresholds or deltas to unlock narrative beats.

- **World State Memory**: Maintain global mood flags (gossip level, crime rate, festival hype) that influence orchestrator weighting and unlock context-sensitive scenes.
- **Reputation Layer**: Track public perception of MC/NPCs (fame, notoriety) to gate events like VIP access, fan confrontations, or police scrutiny.
- **Collections & Goals**: Surface medium-term objectives (complete cafe shifts, gather outfits) so the orchestrator can seed relevant opportunities and reward loops.
- **Seasons & Weather Hooks**: Seasonal toggles and forecast data steer asset selection and event availability without duplicating nodes.
- **Debug Timeline**: Creator-facing timeline showing orchestrator choices, asset picks, and state deltas for tuning.
- **Stat Tracks**: Core stats include new interpersonal meters like arousal and flirtiness alongside energy, stress, etc., all user-extendable with custom rules.

- **Stat Abstractions**: Graph editor stays conceptual—creators tag edges with adjectives (low trust, warming up) or simple sliders; AI/heuristics translate those into concrete numbers (e.g., trust 20 vs 70) during runtime scoring.
    - Tag taxonomy (e.g., ice_cold, wary, open, bonded) with default numeric ranges, customizable per persona.
    - Context-aware scaling: base values adjusted by world state, recent events, or stat trends.
    - Randomized nuance: small jitter within range to avoid rigid repetition.
    - Override hooks: plugins/persona configs can supply custom translators.



- **Advanced Mode**: Optional editor view exposes raw numbers, hidden stats, and overrides for power users while default mode keeps interactions conceptual and tag-driven.





- **Multi-role Nodes**: Any location/person/etc. can stack role descriptors (workplace, event_space, hangout) so a single node serves multiple purposes without duplication.

