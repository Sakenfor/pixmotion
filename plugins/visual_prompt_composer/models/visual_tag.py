"""
Visual Tag Data Models

Core data structures for representing visual elements in the scene composer.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


class ElementType(Enum):
    OBJECT = "object"
    CHARACTER = "character"
    ENVIRONMENT = "environment"
    LIGHT = "light"
    CAMERA = "camera"
    EFFECT = "effect"


class DescriptorProfile(Enum):
    ANATOMICAL_PRECISE = "anatomical_precise"
    MATERIAL_STRUCTURAL = "material_structural"
    ATMOSPHERIC_MELLOW = "atmospheric_mellow"
    EMOTIONAL_EXPRESSIVE = "emotional_expressive"
    CINEMATIC_DRAMATIC = "cinematic_dramatic"
    TECHNICAL_MECHANICAL = "technical_mechanical"


class RelationType(Enum):
    """Types of spatial relationships between visual tags"""
    ADJACENT = "adjacent"
    BEHIND = "behind"
    IN_FRONT = "in_front"
    PARTIALLY_BEHIND = "partially_behind"
    INSIDE = "inside"
    CONTAINS = "contains"
    NEAR = "near"
    FAR = "far"
    ABOVE = "above"
    BELOW = "below"
    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"


@dataclass
class Vector3D:
    """3D vector for positions, rotations, and scales"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def magnitude(self) -> float:
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5

    def normalize(self) -> 'Vector3D':
        mag = self.magnitude()
        if mag == 0:
            return Vector3D()
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)


@dataclass
class Transform:
    """Transform information for visual elements"""
    position: Vector3D = field(default_factory=Vector3D)
    rotation: Vector3D = field(default_factory=Vector3D)
    scale: Vector3D = field(default_factory=lambda: Vector3D(1.0, 1.0, 1.0))

    def copy(self) -> 'Transform':
        return Transform(
            position=Vector3D(self.position.x, self.position.y, self.position.z),
            rotation=Vector3D(self.rotation.x, self.rotation.y, self.rotation.z),
            scale=Vector3D(self.scale.x, self.scale.y, self.scale.z)
        )


@dataclass
class Keyframe:
    """Animation keyframe data"""
    time: float
    value: Any
    interpolation: str = "linear"  # linear, ease_in, ease_out, ease_in_out, cubic


@dataclass
class AnimationCurve:
    """Animation curve with keyframes"""
    property_name: str
    keyframes: List[Keyframe] = field(default_factory=list)

    def add_keyframe(self, time: float, value: Any, interpolation: str = "linear"):
        # Remove existing keyframe at same time
        self.keyframes = [kf for kf in self.keyframes if kf.time != time]

        # Add new keyframe and sort by time
        self.keyframes.append(Keyframe(time, value, interpolation))
        self.keyframes.sort(key=lambda kf: kf.time)

    def get_value_at_time(self, time: float) -> Any:
        """Get interpolated value at given time"""
        if not self.keyframes:
            return None

        # If before first keyframe, return first value
        if time <= self.keyframes[0].time:
            return self.keyframes[0].value

        # If after last keyframe, return last value
        if time >= self.keyframes[-1].time:
            return self.keyframes[-1].value

        # Find surrounding keyframes
        for i in range(len(self.keyframes) - 1):
            kf1 = self.keyframes[i]
            kf2 = self.keyframes[i + 1]

            if kf1.time <= time <= kf2.time:
                # Linear interpolation for now (can be enhanced)
                t = (time - kf1.time) / (kf2.time - kf1.time)

                # Handle different value types
                if isinstance(kf1.value, (int, float)):
                    return kf1.value + t * (kf2.value - kf1.value)
                elif isinstance(kf1.value, Vector3D):
                    return Vector3D(
                        kf1.value.x + t * (kf2.value.x - kf1.value.x),
                        kf1.value.y + t * (kf2.value.y - kf1.value.y),
                        kf1.value.z + t * (kf2.value.z - kf1.value.z)
                    )
                else:
                    # For discrete values, use step interpolation
                    return kf1.value if t < 0.5 else kf2.value

        return None


@dataclass
class SpatialRelationship:
    """Describes spatial relationship between elements"""
    type: str  # "occlusion", "embedding", "contact", "proximity", "layering"
    target_id: str
    strength: float = 1.0  # 0.0 to 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def describe(self) -> str:
        """Generate human-readable description of relationship"""
        descriptions = {
            "occlusion": f"partially obscures {self.properties.get('coverage', '50%')} of",
            "embedding": "is nestled within",
            "contact": "presses against",
            "proximity": "hovers near",
            "layering": "sits atop"
        }
        return descriptions.get(self.type, "relates to")


@dataclass
class AIProfile:
    """AI descriptor profile for controlling description style"""
    profile_type: DescriptorProfile
    descriptiveness: float = 0.8  # 0.0 to 1.0
    style_modifiers: List[str] = field(default_factory=list)
    keywords: Dict[str, float] = field(default_factory=dict)  # keyword -> weight
    inheritance_mode: str = "blend"  # "override", "blend", "inherit"

    def blend_with(self, other: 'AIProfile', blend_factor: float) -> 'AIProfile':
        """Blend this profile with another"""
        blended_descriptiveness = self.descriptiveness * (1 - blend_factor) + other.descriptiveness * blend_factor

        blended_keywords = self.keywords.copy()
        for keyword, weight in other.keywords.items():
            if keyword in blended_keywords:
                blended_keywords[keyword] = blended_keywords[keyword] * (1 - blend_factor) + weight * blend_factor
            else:
                blended_keywords[keyword] = weight * blend_factor

        return AIProfile(
            profile_type=self.profile_type,
            descriptiveness=blended_descriptiveness,
            style_modifiers=self.style_modifiers + other.style_modifiers,
            keywords=blended_keywords,
            inheritance_mode=self.inheritance_mode
        )


@dataclass
class VisualTag:
    """Core visual element in the scene"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    element_type: ElementType = ElementType.OBJECT
    transform: Transform = field(default_factory=Transform)

    # AI Profile system
    primary_profile: AIProfile = field(default_factory=lambda: AIProfile(DescriptorProfile.ANATOMICAL_PRECISE))
    secondary_profile: Optional[AIProfile] = None
    profile_blend: float = 0.0  # 0.0 = primary only, 1.0 = secondary only

    # Animation system
    animations: List[AnimationCurve] = field(default_factory=list)

    # Spatial relationships
    spatial_relationships: List[SpatialRelationship] = field(default_factory=list)

    # Visual properties
    visible: bool = True
    opacity: float = 1.0  # 0.0 (transparent) to 1.0 (opaque)
    selected: bool = False

    # Custom properties
    properties: Dict[str, Any] = field(default_factory=dict)

    def get_effective_profile(self) -> AIProfile:
        """Get the effective AI profile considering blending"""
        if self.secondary_profile is None or self.profile_blend == 0.0:
            return self.primary_profile
        elif self.profile_blend == 1.0:
            return self.secondary_profile
        else:
            return self.primary_profile.blend_with(self.secondary_profile, self.profile_blend)

    def add_animation(self, property_name: str) -> AnimationCurve:
        """Add new animation curve for a property"""
        # Remove existing animation for this property
        self.animations = [anim for anim in self.animations if anim.property_name != property_name]

        # Add new animation curve
        curve = AnimationCurve(property_name)
        self.animations.append(curve)
        return curve

    def get_animation(self, property_name: str) -> Optional[AnimationCurve]:
        """Get animation curve for a property"""
        for anim in self.animations:
            if anim.property_name == property_name:
                return anim
        return None

    def get_state_at_time(self, time: float) -> 'VisualTag':
        """Get interpolated state of this tag at specific time"""
        # Create a copy of the tag
        result = VisualTag(
            id=self.id,
            name=self.name,
            element_type=self.element_type,
            transform=self.transform.copy(),
            primary_profile=self.primary_profile,
            secondary_profile=self.secondary_profile,
            profile_blend=self.profile_blend,
            animations=self.animations,
            spatial_relationships=self.spatial_relationships,
            properties=self.properties.copy(),
            visible=self.visible,
            selected=self.selected
        )

        # Apply animations
        for anim in self.animations:
            value = anim.get_value_at_time(time)
            if value is not None:
                if anim.property_name == "position":
                    result.transform.position = value
                elif anim.property_name == "rotation":
                    result.transform.rotation = value
                elif anim.property_name == "scale":
                    result.transform.scale = value
                elif anim.property_name == "profile_blend":
                    result.profile_blend = value
                else:
                    # Custom property
                    result.properties[anim.property_name] = value

        return result

    def add_spatial_relationship(self, relationship: SpatialRelationship):
        """Add spatial relationship to another element"""
        # Remove existing relationship of same type to same target
        self.spatial_relationships = [
            rel for rel in self.spatial_relationships
            if not (rel.type == relationship.type and rel.target_id == relationship.target_id)
        ]
        self.spatial_relationships.append(relationship)

    def get_spatial_relationships_of_type(self, relationship_type: str) -> List[SpatialRelationship]:
        """Get all spatial relationships of a specific type"""
        return [rel for rel in self.spatial_relationships if rel.type == relationship_type]