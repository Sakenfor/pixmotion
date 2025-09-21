from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


def _normalize_string_list(values) -> List[str]:
    normalized: List[str] = []
    for value in values or []:
        text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized


def _normalize_mapping_of_lists(source) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    if not isinstance(source, Mapping):
        return result

    for key, values in source.items():
        key_text = str(key).strip()
        if not key_text:
            continue
        if isinstance(values, Mapping):
            # Allow nested mapping with ``values`` and/or ``items`` keys.
            nested_values = values.get("values") or values.get("items")
            normalized_values = _normalize_string_list(nested_values)
        elif isinstance(values, (list, tuple, set)):
            normalized_values = _normalize_string_list(values)
        else:
            normalized_values = _normalize_string_list([values])

        if normalized_values:
            result[key_text] = normalized_values

    return result


@dataclass(slots=True)
class AssetManifest:
    uuid: str
    name: str
    type: str
    version: str
    tags: List[str] = field(default_factory=list)
    path: str = ""
    manifest_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        *,
        root_path: str,
        manifest_path: str,
    ) -> "AssetManifest":
        known_keys = {"uuid", "name", "type", "version", "tags"}
        metadata = {
            key: value
            for key, value in data.items()
            if key not in known_keys
        }
        return cls(
            uuid=str(data["uuid"]),
            name=str(data.get("name", "")),
            type=str(data.get("type", "")),
            version=str(data.get("version", "")),
            tags=_normalize_string_list(data.get("tags", [])),
            path=root_path,
            manifest_path=manifest_path,
            metadata=metadata,
        )


@dataclass(slots=True)
class EmotionIntentConfig:
    paths: List[str] = field(default_factory=list)
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmotionPackageManifest(AssetManifest):
    persona_ids: List[str] = field(default_factory=list)
    context_tags: List[str] = field(default_factory=list)
    supported_tones: List[str] = field(default_factory=list)
    intents: Dict[str, EmotionIntentConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        *,
        root_path: str,
        manifest_path: str,
    ) -> "EmotionPackageManifest":
        base = AssetManifest.from_dict(
            data, root_path=root_path, manifest_path=manifest_path
        )

        persona_ids = _normalize_string_list(data.get("persona_ids"))
        if not persona_ids and data.get("persona_id") is not None:
            persona_ids = _normalize_string_list([data.get("persona_id")])

        context_tags = _normalize_string_list(data.get("context_tags", []))
        supported_tones = _normalize_string_list(data.get("supported_tones", []))

        intents: Dict[str, EmotionIntentConfig] = {}
        intents_payload = data.get("intents", {})
        if isinstance(intents_payload, Mapping):
            for intent_name, payload in intents_payload.items():
                name = str(intent_name).strip()
                if not name:
                    continue

                paths: List[str]
                weight = 1.0
                metadata: Dict[str, Any] = {}

                if isinstance(payload, Mapping):
                    raw_paths = payload.get("paths")
                    if raw_paths is None and "path" in payload:
                        raw_paths = [payload["path"]]
                    paths = _normalize_string_list(raw_paths or [])
                    weight_value = payload.get("weight", 1.0)
                    try:
                        weight = float(weight_value)
                    except (TypeError, ValueError):
                        weight = 1.0
                    metadata = {
                        key: value
                        for key, value in payload.items()
                        if key not in {"paths", "path", "weight"}
                    }
                elif isinstance(payload, (list, tuple, set)):
                    paths = _normalize_string_list(payload)
                else:
                    paths = _normalize_string_list([payload])

                intents[name] = EmotionIntentConfig(
                    paths=paths,
                    weight=weight,
                    metadata=metadata,
                )

        return cls(
            uuid=base.uuid,
            name=base.name,
            type=base.type,
            version=base.version,
            tags=base.tags,
            path=base.path,
            manifest_path=base.manifest_path,
            metadata=base.metadata,
            persona_ids=persona_ids,
            context_tags=context_tags,
            supported_tones=supported_tones,
            intents=intents,
        )


@dataclass(slots=True)
class PluginManifest(AssetManifest):
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    trust_level: str = "core"
    capabilities: List[str] = field(default_factory=list)
    provides: Dict[str, List[str]] = field(default_factory=dict)
    requires_features: List[str] = field(default_factory=list)
    init_phase: str = "default"

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        *,
        root_path: str,
        manifest_path: str,
        trust_level: str,
    ) -> "PluginManifest":
        base = AssetManifest.from_dict(
            data, root_path=root_path, manifest_path=manifest_path
        )
        entry_point = str(data.get("entry_point", "")).strip()
        dependencies = _normalize_string_list(data.get("dependencies", []))
        optional_dependencies = _normalize_string_list(
            data.get("optional_dependencies", [])
        )
        capabilities = _normalize_string_list(data.get("capabilities", []))
        provides = _normalize_mapping_of_lists(data.get("provides", {}))
        requires_features = _normalize_string_list(data.get("requires_features", []))
        init_phase = str(data.get("init_phase", "default")).strip() or "default"

        return cls(
            uuid=base.uuid,
            name=base.name,
            type=base.type,
            version=base.version,
            tags=base.tags,
            path=base.path,
            manifest_path=base.manifest_path,
            metadata=base.metadata,
            entry_point=entry_point,
            dependencies=dependencies,
            optional_dependencies=optional_dependencies,
            trust_level=trust_level,
            capabilities=capabilities,
            provides=provides,
            requires_features=requires_features,
            init_phase=init_phase,
        )
