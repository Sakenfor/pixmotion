"""
Scene Graph Data Models

Data structures for managing complete scenes and their hierarchical relationships.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import uuid
import json
from .visual_tag import VisualTag, AIProfile, DescriptorProfile


@dataclass
class PromptSegment:
    """Generated prompt segment for a time range"""
    start_time: float
    end_time: float
    content: str
    tags_involved: List[str] = field(default_factory=list)
    spatial_descriptions: List[str] = field(default_factory=list)
    animation_descriptions: List[str] = field(default_factory=list)
    confidence: float = 1.0  # AI confidence in description


@dataclass
class Scene:
    """Complete scene with all visual elements and properties"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Scene"
    duration: float = 5.0  # seconds

    # Scene elements
    visual_tags: Dict[str, VisualTag] = field(default_factory=dict)

    # Global scene properties
    scene_profile: AIProfile = field(default_factory=lambda: AIProfile(DescriptorProfile.ATMOSPHERIC_MELLOW))
    composition_guides: List[str] = field(default_factory=list)

    # Canvas properties
    canvas_size: Tuple[int, int] = (1920, 1080)
    depth_planes: List[str] = field(default_factory=lambda: ["background", "midground", "foreground"])

    # Background media
    background_asset_id: Optional[str] = None  # Asset ID from asset library
    background_type: Optional[str] = None      # "image" or "video"
    background_video_time: float = 0.0         # Time position for video backgrounds
    background_opacity: float = 1.0            # Background opacity (0.0 to 1.0)
    background_scale: float = 1.0              # Background scale factor

    # Timeline properties
    current_time: float = 0.0
    playback_speed: float = 1.0

    # Metadata
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    version: str = "1.0"

    def add_visual_tag(self, tag: VisualTag) -> bool:
        """Add a visual tag to the scene"""
        if tag.id in self.visual_tags:
            return False
        self.visual_tags[tag.id] = tag
        return True

    def remove_visual_tag(self, tag_id: str) -> bool:
        """Remove a visual tag from the scene"""
        if tag_id not in self.visual_tags:
            return False

        # Remove spatial relationships that reference this tag
        for other_tag in self.visual_tags.values():
            other_tag.spatial_relationships = [
                rel for rel in other_tag.spatial_relationships
                if rel.target_id != tag_id
            ]

        # Remove the tag
        del self.visual_tags[tag_id]
        return True

    def get_visual_tag(self, tag_id: str) -> Optional[VisualTag]:
        """Get a visual tag by ID"""
        return self.visual_tags.get(tag_id)

    def get_tags_by_type(self, element_type) -> List[VisualTag]:
        """Get all visual tags of a specific type"""
        return [tag for tag in self.visual_tags.values() if tag.element_type == element_type]

    def get_tags_at_depth_plane(self, depth_plane: str) -> List[VisualTag]:
        """Get all tags at a specific depth plane"""
        return [
            tag for tag in self.visual_tags.values()
            if tag.properties.get("depth_plane", "midground") == depth_plane
        ]

    def get_scene_at_time(self, time: float) -> 'Scene':
        """Get the scene state at a specific time with interpolated values"""
        # Create a copy of the scene
        scene_copy = Scene(
            id=self.id,
            name=self.name,
            duration=self.duration,
            scene_profile=self.scene_profile,
            composition_guides=self.composition_guides.copy(),
            canvas_size=self.canvas_size,
            depth_planes=self.depth_planes.copy(),
            current_time=time,
            playback_speed=self.playback_speed,
            created_at=self.created_at,
            modified_at=self.modified_at,
            version=self.version
        )

        # Get interpolated state of all tags
        scene_copy.visual_tags = {
            tag_id: tag.get_state_at_time(time)
            for tag_id, tag in self.visual_tags.items()
        }

        return scene_copy

    def get_tags_by_depth_order(self, time: float = None) -> List[VisualTag]:
        """Get all tags ordered by their Z-depth (back to front)"""
        if time is not None:
            scene_at_time = self.get_scene_at_time(time)
            tags = list(scene_at_time.visual_tags.values())
        else:
            tags = list(self.visual_tags.values())

        # Sort by Z position (smaller Z = further back)
        return sorted(tags, key=lambda tag: tag.transform.position.z)

    def detect_state_changes(self, time_range: Tuple[float, float], resolution: float = 0.1) -> List[float]:
        """Detect significant state changes in the scene over time"""
        start_time, end_time = time_range
        change_times = set()

        # Check for keyframe times
        for tag in self.visual_tags.values():
            for anim in tag.animations:
                for keyframe in anim.keyframes:
                    if start_time <= keyframe.time <= end_time:
                        change_times.add(keyframe.time)

        # Sample scene at regular intervals to detect other changes
        current_time = start_time
        previous_state = None

        while current_time <= end_time:
            current_state = self.get_scene_at_time(current_time)

            if previous_state is not None:
                if self._scenes_significantly_different(previous_state, current_state):
                    change_times.add(current_time)

            previous_state = current_state
            current_time += resolution

        return sorted(list(change_times))

    def _scenes_significantly_different(self, scene1: 'Scene', scene2: 'Scene', threshold: float = 0.1) -> bool:
        """Check if two scene states are significantly different"""
        if len(scene1.visual_tags) != len(scene2.visual_tags):
            return True

        for tag_id, tag1 in scene1.visual_tags.items():
            tag2 = scene2.visual_tags.get(tag_id)
            if not tag2:
                return True

            # Check position changes
            pos_diff = tag1.transform.position - tag2.transform.position
            if pos_diff.magnitude() > threshold:
                return True

            # Check profile blend changes
            if abs(tag1.profile_blend - tag2.profile_blend) > threshold:
                return True

            # Check significant property changes
            for key, value1 in tag1.properties.items():
                value2 = tag2.properties.get(key)
                if value1 != value2:
                    if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                        if abs(value1 - value2) > threshold:
                            return True
                    else:
                        return True

        return False

    def get_active_tags_at_time(self, time: float) -> List[VisualTag]:
        """Get only visible and active tags at specific time"""
        scene_at_time = self.get_scene_at_time(time)
        return [tag for tag in scene_at_time.visual_tags.values() if tag.visible]

    def validate(self) -> List[str]:
        """Validate scene for common issues"""
        issues = []

        # Check for duplicate names
        names = [tag.name for tag in self.visual_tags.values() if tag.name]
        if len(names) != len(set(names)):
            issues.append("Duplicate tag names found")

        # Check for invalid spatial relationships
        for tag in self.visual_tags.values():
            for rel in tag.spatial_relationships:
                if rel.target_id not in self.visual_tags:
                    issues.append(f"Tag '{tag.name}' has relationship to non-existent tag '{rel.target_id}'")

        # Check timeline bounds
        for tag in self.visual_tags.values():
            for anim in tag.animations:
                for keyframe in anim.keyframes:
                    if keyframe.time < 0 or keyframe.time > self.duration:
                        issues.append(f"Tag '{tag.name}' has keyframe outside scene duration")

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Serialize scene to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "duration": self.duration,
            "visual_tags": {
                tag_id: self._serialize_tag(tag)
                for tag_id, tag in self.visual_tags.items()
            },
            "scene_profile": self._serialize_ai_profile(self.scene_profile),
            "composition_guides": self.composition_guides,
            "canvas_size": self.canvas_size,
            "depth_planes": self.depth_planes,
            "current_time": self.current_time,
            "playback_speed": self.playback_speed,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "version": self.version
        }

    def _serialize_tag(self, tag: VisualTag) -> Dict[str, Any]:
        """Serialize a visual tag to dictionary"""
        return {
            "id": tag.id,
            "name": tag.name,
            "element_type": tag.element_type.value,
            "transform": {
                "position": {"x": tag.transform.position.x, "y": tag.transform.position.y, "z": tag.transform.position.z},
                "rotation": {"x": tag.transform.rotation.x, "y": tag.transform.rotation.y, "z": tag.transform.rotation.z},
                "scale": {"x": tag.transform.scale.x, "y": tag.transform.scale.y, "z": tag.transform.scale.z}
            },
            "primary_profile": self._serialize_ai_profile(tag.primary_profile),
            "secondary_profile": self._serialize_ai_profile(tag.secondary_profile) if tag.secondary_profile else None,
            "profile_blend": tag.profile_blend,
            "animations": [
                {
                    "property_name": anim.property_name,
                    "keyframes": [
                        {
                            "time": kf.time,
                            "value": self._serialize_value(kf.value),
                            "interpolation": kf.interpolation
                        }
                        for kf in anim.keyframes
                    ]
                }
                for anim in tag.animations
            ],
            "spatial_relationships": [
                {
                    "type": rel.type,
                    "target_id": rel.target_id,
                    "strength": rel.strength,
                    "properties": rel.properties
                }
                for rel in tag.spatial_relationships
            ],
            "properties": tag.properties,
            "visible": tag.visible,
            "selected": tag.selected
        }

    def _serialize_ai_profile(self, profile: AIProfile) -> Dict[str, Any]:
        """Serialize AI profile to dictionary"""
        return {
            "profile_type": profile.profile_type.value,
            "descriptiveness": profile.descriptiveness,
            "style_modifiers": profile.style_modifiers,
            "keywords": profile.keywords,
            "inheritance_mode": profile.inheritance_mode
        }

    def _serialize_value(self, value: Any) -> Any:
        """Serialize animation values"""
        if hasattr(value, 'x') and hasattr(value, 'y') and hasattr(value, 'z'):
            return {"x": value.x, "y": value.y, "z": value.z}
        return value

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        """Deserialize scene from dictionary"""
        # This would implement the reverse of to_dict()
        # For now, return a basic implementation
        scene = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled Scene"),
            duration=data.get("duration", 5.0)
        )
        # TODO: Implement full deserialization
        return scene

    def save_to_file(self, filepath: str) -> bool:
        """Save scene to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to save scene: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional['Scene']:
        """Load scene from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Failed to load scene: {e}")
            return None