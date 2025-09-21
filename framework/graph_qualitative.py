from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Tuple


@dataclass(slots=True)
class DescriptorRange:
    """Canonical numeric range for a qualitative descriptor."""

    name: str
    min_value: float
    max_value: float
    weight: float = 1.0
    jitter: float = 0.0
    aliases: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def clamp(self, value: float) -> float:
        low = min(self.min_value, self.max_value)
        high = max(self.min_value, self.max_value)
        return max(low, min(high, value))


@dataclass(slots=True)
class QualitativeValue:
    """Resolved numeric value plus context about how it was derived."""

    scale_id: str
    descriptor: str
    value: float
    min_value: float
    max_value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class QualitativeResolver:
    """Translates conceptual descriptors into usable numeric values."""

    def __init__(self, registry, log_manager=None):
        self.registry = registry
        self.log = log_manager

    def resolve(
        self,
        scale_id: str,
        descriptor: Optional[str],
        *,
        persona_settings: Optional[Dict[str, Any]] = None,
        context_overrides: Optional[Dict[str, Any]] = None,
        default_descriptor: Optional[str] = None,
        randomize: bool = True,
        rng: Optional[random.Random] = None,
    ) -> Optional[QualitativeValue]:
        """Return a numeric value for the descriptor or ``None`` if unavailable."""

        scale_data = self.registry.get_qualitative_scale(scale_id)
        if not scale_data:
            if self.log:
                self.log.warning("Unknown qualitative scale '%s'", scale_id)
            return None

        scale = _NormalisedScale.from_descriptor(scale_data)
        key = descriptor or default_descriptor or scale.default_descriptor
        if key is None:
            if self.log:
                self.log.warning(
                    "No descriptor specified and scale '%s' lacks a default.",
                    scale_id,
                )
            return None

        descriptor_entry = scale.lookup_descriptor(key)
        if descriptor_entry is None:
            if self.log:
                self.log.warning(
                    "Descriptor '%s' not defined for qualitative scale '%s'",
                    key,
                    scale_id,
                )
            return None

        persona_scale_override = _fetch_nested(
            persona_settings,
            ("qualitative_overrides", scale_id, "scale"),
        )
        persona_descriptor_override = _fetch_nested(
            persona_settings,
            ("qualitative_overrides", scale_id, "descriptors", descriptor_entry.name),
        )
        context_scale_override = _fetch_nested(context_overrides, ("scale",))
        context_descriptor_override = _fetch_nested(
            context_overrides,
            ("descriptors", descriptor_entry.name),
        )

        min_value, max_value = _resolve_range(
            descriptor_entry,
            scale,
            persona_descriptor_override,
            persona_scale_override,
            context_descriptor_override,
            context_scale_override,
        )

        if rng is None:
            rng = random

        base_value = (min_value + max_value) / 2.0
        if randomize:
            low, high = sorted((min_value, max_value))
            base_value = rng.uniform(low, high)

        jitter_budget = _collect_jitter_values(
            scale,
            descriptor_entry,
            persona_scale_override,
            persona_descriptor_override,
            context_scale_override,
            context_descriptor_override,
        )
        if jitter_budget:
            span = abs(max_value - min_value) or 1.0
            for jitter in jitter_budget:
                base_value += _compute_jitter(jitter, span, rng)

        adjustments: Iterable[Dict[str, Any]] = tuple(
            item
            for item in (
                scale.adjustments,
                descriptor_entry.metadata.get("adjustments"),
                _safe_dict(persona_scale_override).get("adjustments"),
                _safe_dict(persona_descriptor_override).get("adjustments"),
                _safe_dict(context_scale_override).get("adjustments"),
                _safe_dict(context_descriptor_override).get("adjustments"),
            )
            if isinstance(item, dict)
        )

        value = base_value
        for adjustment in adjustments:
            value = _apply_adjustment(value, adjustment)

        bounds = scale.bounds
        if bounds:
            value = max(bounds[0], min(bounds[1], value))

        metadata = dict(descriptor_entry.metadata)
        metadata.setdefault("resolved_descriptor", descriptor_entry.name)
        if persona_descriptor_override:
            metadata["persona_override"] = persona_descriptor_override
        if context_descriptor_override:
            metadata["context_override"] = context_descriptor_override

        return QualitativeValue(
            scale_id=scale_id,
            descriptor=descriptor_entry.name,
            value=value,
            min_value=min_value,
            max_value=max_value,
            metadata=metadata,
        )


@dataclass(slots=True)
class _NormalisedScale:
    scale_id: str
    descriptors: Dict[str, DescriptorRange]
    alias_map: Dict[str, DescriptorRange]
    default_descriptor: Optional[str]
    bounds: Optional[Tuple[float, float]]
    adjustments: Optional[Dict[str, Any]]
    jitter: float
    metadata: Dict[str, Any]

    @classmethod
    def from_descriptor(cls, descriptor: Dict[str, Any]) -> "_NormalisedScale":
        descriptors: Dict[str, DescriptorRange] = {}
        alias_map: Dict[str, DescriptorRange] = {}
        raw_descriptors = descriptor.get("descriptors", [])
        for entry in raw_descriptors:
            normalised = _normalise_descriptor(entry)
            descriptors[normalised.name] = normalised
            alias_map[normalised.name.lower()] = normalised
            for alias in normalised.aliases:
                alias_map[alias.lower()] = normalised

        default_descriptor = descriptor.get("default_descriptor") or descriptor.get("default")
        if isinstance(default_descriptor, str):
            resolved = alias_map.get(default_descriptor.lower())
            default_descriptor = resolved.name if resolved else default_descriptor
        else:
            default_descriptor = None

        bounds = None
        raw_bounds = descriptor.get("bounds") or descriptor.get("range")
        if isinstance(raw_bounds, (list, tuple)) and len(raw_bounds) == 2:
            try:
                bounds = (float(raw_bounds[0]), float(raw_bounds[1]))
            except (TypeError, ValueError):
                bounds = None

        jitter = 0.0
        raw_jitter = descriptor.get("jitter")
        if isinstance(raw_jitter, (int, float)):
            jitter = float(raw_jitter)

        metadata = dict(descriptor.get("metadata", {}))

        adjustments = descriptor.get("adjustments")
        if not isinstance(adjustments, dict):
            adjustments = None

        return cls(
            scale_id=str(descriptor.get("id", "")),
            descriptors=descriptors,
            alias_map=alias_map,
            default_descriptor=default_descriptor,
            bounds=bounds,
            adjustments=adjustments,
            jitter=jitter,
            metadata=metadata,
        )

    def lookup_descriptor(self, key: str) -> Optional[DescriptorRange]:
        if not key:
            return None
        candidate = self.alias_map.get(key.strip().lower())
        if candidate:
            return candidate
        token = key.strip().lower().split(":")[-1].strip(" +")
        return self.alias_map.get(token)


def _normalise_descriptor(data: Dict[str, Any]) -> DescriptorRange:
    name = str(data.get("name") or data.get("id"))
    raw_aliases = data.get("aliases") or data.get("tags")
    if raw_aliases is None:
        aliases: Tuple[str, ...] = ()
    elif isinstance(raw_aliases, (list, tuple, set)):
        aliases = tuple(str(alias).lower() for alias in raw_aliases)
    else:
        aliases = (str(raw_aliases).lower(),)

    range_values = data.get("range") or (data.get("min"), data.get("max"))
    if isinstance(range_values, (list, tuple)) and len(range_values) == 2:
        min_value, max_value = range_values
    else:
        min_value = data.get("min", 0)
        max_value = data.get("max", min_value)

    try:
        min_value = float(min_value)
    except (TypeError, ValueError):
        min_value = 0.0
    try:
        max_value = float(max_value)
    except (TypeError, ValueError):
        max_value = min_value

    weight = data.get("weight", 1.0)
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        weight = 1.0

    jitter = data.get("jitter", 0.0)
    try:
        jitter = float(jitter)
    except (TypeError, ValueError):
        jitter = 0.0

    metadata = dict(data.get("metadata", {}))
    metadata.setdefault("raw", dict(data))

    return DescriptorRange(
        name=name,
        min_value=min_value,
        max_value=max_value,
        weight=weight,
        jitter=jitter,
        aliases=aliases,
        metadata=metadata,
    )


def _resolve_range(
    descriptor: DescriptorRange,
    scale: _NormalisedScale,
    persona_descriptor_override: Optional[Dict[str, Any]],
    persona_scale_override: Optional[Dict[str, Any]],
    context_descriptor_override: Optional[Dict[str, Any]],
    context_scale_override: Optional[Dict[str, Any]],
) -> Tuple[float, float]:
    min_value = descriptor.min_value
    max_value = descriptor.max_value

    for override in (
        scale.metadata.get("defaults"),
        _safe_dict(persona_scale_override).get("defaults"),
        _safe_dict(context_scale_override).get("defaults"),
        persona_descriptor_override,
        context_descriptor_override,
    ):
        if not isinstance(override, dict):
            continue
        if "range" in override and isinstance(override["range"], (list, tuple)) and len(override["range"]) == 2:
            try:
                min_value = float(override["range"][0])
                max_value = float(override["range"][1])
                continue
            except (TypeError, ValueError):
                pass
        if "min" in override or "max" in override:
            try:
                if "min" in override:
                    min_value = float(override["min"])
                if "max" in override:
                    max_value = float(override["max"])
            except (TypeError, ValueError):
                continue

    if min_value > max_value:
        min_value, max_value = max_value, min_value

    bounds = scale.bounds
    if bounds:
        min_value = max(bounds[0], min_value)
        max_value = min(bounds[1], max_value)

    return min_value, max_value


def _collect_jitter_values(*sources: Any) -> Tuple[float, ...]:
    values: list[float] = []
    for source in sources:
        values.extend(_extract_jitter(source))
    return tuple(values)


def _extract_jitter(source: Any) -> Tuple[float, ...]:
    if source is None:
        return ()
    if isinstance(source, _NormalisedScale):
        return (source.jitter,) if source.jitter else ()
    if isinstance(source, DescriptorRange):
        return (source.jitter,) if source.jitter else ()
    if isinstance(source, dict) and "jitter" in source:
        try:
            jitter = float(source["jitter"])
            return (jitter,)
        except (TypeError, ValueError):
            return ()
    return ()


def _compute_jitter(jitter: float, span: float, rng: random.Random) -> float:
    if jitter == 0:
        return 0.0
    amplitude = abs(jitter)
    if -1.0 <= jitter <= 1.0:
        amplitude = span * abs(jitter)
    direction = rng.uniform(-1.0, 1.0)
    return amplitude * direction


def _apply_adjustment(value: float, adjustment: Dict[str, Any]) -> float:
    result = value
    multiplier = adjustment.get("multiplier")
    if multiplier is not None:
        try:
            result *= float(multiplier)
        except (TypeError, ValueError):
            pass
    bias = adjustment.get("bias")
    if bias is not None:
        try:
            result += float(bias)
        except (TypeError, ValueError):
            pass
    for key in ("min", "min_value"):
        if key in adjustment:
            try:
                result = max(float(adjustment[key]), result)
            except (TypeError, ValueError):
                pass
            break
    for key in ("max", "max_value"):
        if key in adjustment:
            try:
                result = min(float(adjustment[key]), result)
            except (TypeError, ValueError):
                pass
            break
    return result


def _safe_dict(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _fetch_nested(value: Optional[Dict[str, Any]], path: Tuple[Any, ...]):
    current: Any = value
    for key in path:
        if current is None:
            return None
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current



