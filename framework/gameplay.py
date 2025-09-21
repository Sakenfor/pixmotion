from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .graph_schema import GraphDocument
from .graph_qualitative import QualitativeResolver, QualitativeValue


def _resolve_class_reference(reference: Any):
    if not isinstance(reference, str):
        return reference

    module_name, sep, attr = reference.partition(":")
    if not sep:
        module_name, attr = reference.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr)


@dataclass(slots=True)
class PromptIntent:
    action: str
    subject: Optional[str] = None
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PromptResult:
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PromptSuggestion:
    text: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BasePromptHandler:
    """Converts player input into intents and can suggest follow-up prompts."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.log_manager

    def parse_prompt(
        self, prompt_text: str, state: Dict[str, Any]
    ) -> Optional[PromptIntent]:
        raise NotImplementedError

    def suggest_prompts(
        self, state: Dict[str, Any]
    ) -> Iterable[PromptSuggestion]:
        return []


class BasePromptSuggester:
    """Produces context-aware prompt suggestions for the player."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.log_manager

    def suggest_prompts(
        self, state: Dict[str, Any]
    ) -> Iterable[PromptSuggestion]:
        return []


class BaseOrchestrator:
    """Coordinates scenario flow given templates, state, and player intents."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.log_manager

    def configure(self, *, scenario: Dict[str, Any]) -> None:
        """Called after the orchestrator is activated so it can bootstrap state."""

    def handle_intent(
        self, intent: PromptIntent, state: Dict[str, Any]
    ) -> PromptResult:
        raise NotImplementedError

    def advance_time(
        self, state: Dict[str, Any], *, delta_minutes: int = 0
    ) -> None:
        """Allows the orchestrator to update state as time progresses."""


class GameplayRuntime:
    """Central coordination layer for gameplay-centric plugins."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.log_manager
        self.template_registry = framework.template_registry
        self.graph_registry = framework.graph_registry
        self.graph_store = framework.graph_store
        self._qualitative_resolver = QualitativeResolver(self.graph_registry, self.log)
        self._state: Dict[str, Any] = {}
        self._active_graph_id: Optional[str] = None
        self._active_graph: Optional[GraphDocument] = None
        self._active_persona_id: Optional[str] = None
        self._active_persona_settings: Dict[str, Any] = {}
        self._runtime_handler_instances: Dict[str, Any] = {}
        self._orchestrators: Dict[str, Dict[str, Any]] = {}
        self._prompt_handlers: Dict[str, Dict[str, Any]] = {}
        self._prompt_suggesters: Dict[str, Dict[str, Any]] = {}
        self._minigames: Dict[str, Dict[str, Any]] = {}
        self._active_orchestrator_id: Optional[str] = None
        self._active_orchestrator: Optional[BaseOrchestrator] = None

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    def reset_state(self) -> None:
        self._state = {}
        self._active_graph_id = None
        self._active_graph = None
        self._active_persona_id = None
        self._active_persona_settings = {}


    def load_graph(self, graph_id: str) -> Optional[GraphDocument]:
        graph = self.graph_store.get(graph_id)
        if not graph:
            self.log.error("Graph '%s' could not be found in the store.", graph_id)
            return None
        self._active_graph_id = graph_id
        self._active_graph = graph.copy()
        self.log.info("Graph '%s' activated in runtime.", graph_id)
        return graph.copy()

    def get_active_graph(self) -> Optional[GraphDocument]:
        if not self._active_graph:
            return None
        return self._active_graph.copy()

    def get_active_graph_id(self) -> Optional[str]:
        return self._active_graph_id

    def set_active_persona(self, persona_id: str, overrides: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        descriptor = self.graph_registry.get_persona(persona_id)
        if not descriptor:
            self.log.error("Unknown persona '%s'.", persona_id)
            return None
        settings = dict(descriptor.get("settings", {}))
        if overrides:
            settings.update(overrides)
        self._active_persona_id = persona_id
        self._active_persona_settings = settings
        persona_state = self._state.setdefault("persona", {})
        persona_state["id"] = persona_id
        persona_state["settings"] = settings
        self.log.info("Persona '%s' activated.", persona_id)
        return settings

    def clear_persona(self) -> None:
        self._active_persona_id = None
        self._active_persona_settings = {}
        self._state.pop("persona", None)

    def resolve_qualitative(
        self,
        scale_id: str,
        descriptor: Optional[str],
        *,
        context_overrides: Optional[Dict[str, Any]] = None,
        default_descriptor: Optional[str] = None,
        randomize: bool = True,
        rng: Any = None,
    ) -> Optional[QualitativeValue]:
        """Translate a conceptual descriptor into a numeric value using the active persona."""

        persona_settings = self._active_persona_settings or {}
        return self._qualitative_resolver.resolve(
            scale_id,
            descriptor,
            persona_settings=persona_settings,
            context_overrides=context_overrides,
            default_descriptor=default_descriptor,
            randomize=randomize,
            rng=rng,
        )

    def select_emotion_loop(
        self,
        *,
        intent: str,
        tone: Optional[str] = None,
        context_tags: Optional[Iterable[str]] = None,
        avoid_recent: bool = True,
        seed: Optional[int] = None,
        avoid_asset_ids: Optional[Iterable[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        selector = self.framework.get_service("emotion_loop_selector")
        if not selector:
            self.log.warning("Emotion loop selector service is not available.")
            return None

        persona_id = self._active_persona_id
        context_list = list(context_tags) if context_tags else None
        recent_state: List[str] | None = None
        if avoid_recent:
            emotion_state = self._state.setdefault("emotion", {})
            recent_state = emotion_state.setdefault("recent", [])

        selection = selector.select_clip(
            persona_id=persona_id,
            intent=intent,
            tone=tone,
            context_tags=context_list,
            recent_asset_ids=list(recent_state) if recent_state else None,
            avoid_asset_ids=list(avoid_asset_ids) if avoid_asset_ids else None,
            seed=seed,
        )

        if selection and recent_state is not None:
            recent_state.append(selection.get("asset_id"))
            if len(recent_state) > 6:
                del recent_state[0 : len(recent_state) - 6]
        return selection

    def resolve_qualitative_value(
        self,
        scale_id: str,
        descriptor: Optional[str],
        *,
        context_overrides: Optional[Dict[str, Any]] = None,
        default_descriptor: Optional[str] = None,
        randomize: bool = True,
        rng: Any = None,
        fallback: Optional[float] = None,
    ) -> Optional[float]:
        """Convenience helper that returns only the numeric value."""

        result = self.resolve_qualitative(
            scale_id,
            descriptor,
            context_overrides=context_overrides,
            default_descriptor=default_descriptor,
            randomize=randomize,
            rng=rng,
        )
        if result is None:
            return fallback
        return result.value

    def get_active_persona_id(self) -> Optional[str]:
        return self._active_persona_id

    def get_active_persona_settings(self) -> Dict[str, Any]:
        return dict(self._active_persona_settings)

    def list_personas(self) -> List[Dict[str, Any]]:
        return [dict(value) for value in self.graph_registry.personas.values()]

    def list_action_bundles(self) -> List[Dict[str, Any]]:
        return [dict(value) for value in self.graph_registry.action_bundles.values()]

    def get_action_bundle(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        descriptor = self.graph_registry.get_action_bundle(bundle_id)
        if not descriptor:
            return None
        return dict(descriptor)

    def get_runtime_handler(self, handler_id: str):
        descriptor = self.graph_registry.runtime_handlers.get(handler_id)
        if not descriptor:
            self.log.error("Runtime handler '%s' not registered.", handler_id)
            return None
        return self._get_runtime_handler_instance(handler_id, descriptor)

    def get_relation_handlers(self, relation_type: str) -> List[Any]:
        handlers: List[Any] = []
        for handler_id, descriptor in self.graph_registry.runtime_handlers.items():
            relation_types = descriptor.get("relation_types")
            if relation_types and relation_type not in relation_types:
                continue
            instance = self._get_runtime_handler_instance(handler_id, descriptor)
            if instance is not None:
                handlers.append(instance)
        return handlers

    def invalidate_runtime_handlers(self) -> None:
        self._runtime_handler_instances.clear()

    def _get_runtime_handler_instance(self, handler_id: str, descriptor: Dict[str, Any]):
        instance = self._runtime_handler_instances.get(handler_id)
        if instance is not None:
            return instance
        class_path = descriptor.get("class")
        if not class_path:
            self.log.error("Runtime handler '%s' missing class path.", handler_id)
            return None
        try:
            klass = _resolve_class_reference(class_path)
        except Exception as exc:  # noqa: BLE001
            self.log.error("Failed to resolve runtime handler '%s': %s", handler_id, exc, exc_info=True)
            return None
        instance = klass(self.framework)
        self._runtime_handler_instances[handler_id] = instance
        return instance

    def register_orchestrator(
        self,
        orchestrator_id: str,
        class_reference: Any,
        *,
        plugin_uuid: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        orchestrator_id = orchestrator_id.strip()
        if not orchestrator_id:
            self.log.error("Cannot register orchestrator without an id.")
            return

        self._orchestrators[orchestrator_id] = {
            "class": class_reference,
            "metadata": metadata or {},
            "plugin_uuid": plugin_uuid,
            "instance": None,
        }
        self.log.info(
            "Registered orchestrator '%s' from plugin %s",
            orchestrator_id,
            plugin_uuid,
        )

    def activate_orchestrator(
        self, orchestrator_id: str, *, scenario: Optional[Dict[str, Any]] = None
    ) -> None:
        entry = self._orchestrators.get(orchestrator_id)
        if not entry:
            raise ValueError(f"Unknown orchestrator '{orchestrator_id}'")

        klass = _resolve_class_reference(entry["class"])
        if not klass:
            raise RuntimeError(
                f"Orchestrator class for '{orchestrator_id}' could not be resolved"
            )

        instance = klass(self.framework)
        entry["instance"] = instance
        self._active_orchestrator_id = orchestrator_id
        self._active_orchestrator = instance

        if scenario is not None:
            persona_overrides = None
            raw_overrides = scenario.get("persona_overrides") or scenario.get("persona_settings")
            if isinstance(raw_overrides, dict):
                persona_overrides = dict(raw_overrides)
            persona_spec = scenario.get("persona")
            persona_id = scenario.get("persona_id")
            if isinstance(persona_spec, dict):
                persona_id = persona_id or persona_spec.get("id")
                spec_settings = persona_spec.get("settings")
                if isinstance(spec_settings, dict):
                    if persona_overrides is None:
                        persona_overrides = dict(spec_settings)
                    else:
                        persona_overrides.update(spec_settings)
            if persona_id:
                self.set_active_persona(persona_id, overrides=persona_overrides)
            else:
                self.clear_persona()

            graph_id = scenario.get("graph_id")
            if graph_id:
                self.load_graph(graph_id)
            else:
                self._active_graph_id = None
                self._active_graph = None

            instance.configure(scenario=scenario)

        self.log.info("Activated orchestrator '%s'", orchestrator_id)

    def get_active_orchestrator(self) -> Optional[BaseOrchestrator]:
        return self._active_orchestrator

    def register_prompt_handler(
        self,
        handler_id: str,
        class_reference: Any,
        *,
        plugin_uuid: str,
        priority: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        handler_id = handler_id.strip()
        if not handler_id:
            self.log.error("Cannot register prompt handler without an id.")
            return

        self._prompt_handlers[handler_id] = {
            "class": class_reference,
            "plugin_uuid": plugin_uuid,
            "priority": priority,
            "metadata": metadata or {},
            "instance": None,
        }
        self.log.info(
            "Registered prompt handler '%s' from plugin %s",
            handler_id,
            plugin_uuid,
        )

    def register_prompt_suggester(
        self,
        suggester_id: str,
        class_reference: Any,
        *,
        plugin_uuid: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        suggester_id = suggester_id.strip()
        if not suggester_id:
            self.log.error("Cannot register prompt suggester without an id.")
            return

        self._prompt_suggesters[suggester_id] = {
            "class": class_reference,
            "plugin_uuid": plugin_uuid,
            "metadata": metadata or {},
            "instance": None,
        }
        self.log.info(
            "Registered prompt suggester '%s' from plugin %s",
            suggester_id,
            plugin_uuid,
        )

    def register_minigame(
        self,
        minigame_id: str,
        definition: Dict[str, Any],
        *,
        plugin_uuid: str,
    ) -> None:
        minigame_id = minigame_id.strip()
        if not minigame_id:
            self.log.error("Cannot register minigame without an id.")
            return

        definition = dict(definition)
        definition.setdefault("plugin_uuid", plugin_uuid)
        self._minigames[minigame_id] = definition
        self.log.info("Registered minigame '%s' from plugin %s", minigame_id, plugin_uuid)

    def handle_player_prompt(self, prompt_text: str) -> PromptResult:
        orchestrator = self.get_active_orchestrator()
        if not orchestrator:
            return PromptResult(
                success=False,
                message="No active orchestrator is configured.",
            )

        handlers = sorted(
            self._prompt_handlers.values(),
            key=lambda item: item["priority"],
        )
        for entry in handlers:
            instance = entry.get("instance")
            if instance is None:
                klass = _resolve_class_reference(entry["class"])
                instance = klass(self.framework)
                entry["instance"] = instance

            intent = instance.parse_prompt(prompt_text, self._state)
            if intent is None:
                continue

            return orchestrator.handle_intent(intent, self._state)

        return PromptResult(
            success=False,
            message="None of the registered handlers could interpret the prompt.",
        )

    def get_prompt_suggestions(self) -> List[PromptSuggestion]:
        suggestions: List[PromptSuggestion] = []
        for entry in self._prompt_suggesters.values():
            instance = entry.get("instance")
            if instance is None:
                klass = _resolve_class_reference(entry["class"])
                instance = klass(self.framework)
                entry["instance"] = instance

            suggestions.extend(list(instance.suggest_prompts(self._state)))

        return suggestions

    def list_orchestrators(self) -> List[str]:
        return list(self._orchestrators.keys())

    def list_prompt_handlers(self) -> List[str]:
        return list(self._prompt_handlers.keys())

    def list_minigames(self) -> List[str]:
        return list(self._minigames.keys())

    def clear_plugin_artifacts(self, plugin_uuid: str) -> None:
        for collection in (
            self._orchestrators,
            self._prompt_handlers,
            self._prompt_suggesters,
            self._minigames,
        ):
            to_remove = [
                key for key, entry in collection.items() if entry.get("plugin_uuid") == plugin_uuid
            ]
            for key in to_remove:
                collection.pop(key, None)

    def clear(self) -> None:
        self._state.clear()
        self._orchestrators.clear()
        self._prompt_handlers.clear()
        self._prompt_suggesters.clear()
        self._minigames.clear()
        self._runtime_handler_instances.clear()
        self._active_graph_id = None
        self._active_graph = None
        self._active_persona_id = None
        self._active_persona_settings = {}
        self._active_orchestrator_id = None
        self._active_orchestrator = None



