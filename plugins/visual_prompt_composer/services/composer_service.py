"""
Visual Composer Service

Core service for managing visual scene composition, providing scene operations,
and coordinating between other composer services.
"""

from typing import Optional, List, Dict, Any
from interfaces import IService
from ..models.scene_graph import Scene, PromptSegment
from ..models.visual_tag import VisualTag, ElementType, DescriptorProfile, AIProfile
import os
import json
from datetime import datetime


class VisualComposerService(IService):
    """Core service for visual prompt composition"""

    def initialize(self):
        """Initialize the composer service"""
        self.log = self.framework.get_service("log_manager")
        self.events = self.framework.get_service("event_manager")
        self.settings = self.framework.get_service("settings_service")

        # Initialize state first
        self.current_scene: Optional[Scene] = None
        self.scene_history: List[Scene] = []
        self.max_history = 50

        # Initialize spatial intelligence engine (will be set by plugin)
        self.spatial_engine = None

        # Default scene settings
        self.default_duration = 5.0
        self.default_canvas_size = (1920, 1080)

        self.log.info("Visual Composer Service initialized")

    def set_spatial_engine(self, spatial_engine):
        """Set the spatial intelligence engine reference"""
        self.spatial_engine = spatial_engine

    def new_scene(self, name: str = "Untitled Scene") -> Scene:
        """Create a new scene"""
        try:
            scene = Scene(
                name=name,
                duration=self.default_duration,
                canvas_size=self.default_canvas_size,
                created_at=datetime.utcnow().isoformat()
            )

            self._set_current_scene(scene)
            self.log.info(f"Created new scene: {name}")

            # Publish event
            self.events.publish("composer:scene_created", scene_id=scene.id, name=name)

            return scene

        except Exception as e:
            self.log.error(f"Failed to create new scene: {e}")
            raise

    def save_scene(self, scene: Scene = None, filepath: str = None) -> bool:
        """Save scene to file"""
        try:
            scene_to_save = scene or self.current_scene
            if not scene_to_save:
                self.log.warning("No scene to save")
                return False

            if not filepath:
                # Use default save location
                save_dir = self.settings.resolve_user_path("scenes")
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, f"{scene_to_save.name}.json")

            # Update modified timestamp
            scene_to_save.modified_at = datetime.utcnow().isoformat()

            success = scene_to_save.save_to_file(filepath)
            if success:
                self.log.info(f"Saved scene '{scene_to_save.name}' to {filepath}")
                self.events.publish("composer:scene_saved", scene_id=scene_to_save.id, filepath=filepath)
            else:
                self.log.error(f"Failed to save scene to {filepath}")

            return success

        except Exception as e:
            self.log.error(f"Failed to save scene: {e}")
            return False

    def load_scene(self, filepath: str) -> Optional[Scene]:
        """Load scene from file"""
        try:
            scene = Scene.load_from_file(filepath)
            if scene:
                self._set_current_scene(scene)
                self.log.info(f"Loaded scene '{scene.name}' from {filepath}")
                self.events.publish("composer:scene_loaded", scene_id=scene.id, filepath=filepath)
            else:
                self.log.error(f"Failed to load scene from {filepath}")

            return scene

        except Exception as e:
            self.log.error(f"Failed to load scene: {e}")
            return None

    def get_current_scene(self) -> Optional[Scene]:
        """Get the current scene"""
        return self.current_scene

    def set_current_scene(self, scene: Scene):
        """Set the current scene"""
        self._set_current_scene(scene)

    def _set_current_scene(self, scene: Scene):
        """Internal method to set current scene with history management"""
        if self.current_scene:
            # Add to history
            self.scene_history.append(self.current_scene)
            if len(self.scene_history) > self.max_history:
                self.scene_history.pop(0)

        self.current_scene = scene
        self.events.publish("composer:scene_changed", scene_id=scene.id if scene else None)

    def add_visual_tag(self, tag: VisualTag) -> bool:
        """Add a visual tag to the current scene"""
        try:
            if not self.current_scene:
                self.log.warning("No current scene to add tag to")
                return False

            success = self.current_scene.add_visual_tag(tag)
            if success:
                # Update spatial relationships for the new tag (if spatial engine is available)
                if self.spatial_engine:
                    other_tags = [t for t in self.current_scene.visual_tags.values() if t.id != tag.id]
                    self.spatial_engine.update_tag_spatial_relationships(tag, other_tags)

                    # Update spatial relationships for existing tags with the new tag
                    for other_tag in other_tags:
                        self.spatial_engine.update_tag_spatial_relationships(other_tag, [tag] + [t for t in other_tags if t.id != other_tag.id])

                self.log.debug(f"Added visual tag '{tag.name}' to scene '{self.current_scene.name}'")
                self.events.publish("composer:tag_added", scene_id=self.current_scene.id, tag_id=tag.id)
            else:
                self.log.warning(f"Tag with ID {tag.id} already exists in scene")

            return success

        except Exception as e:
            self.log.error(f"Failed to add visual tag: {e}")
            return False

    def update_visual_tag(self, tag_id: str, updates: Dict[str, Any]) -> bool:
        """Update properties of a visual tag"""
        try:
            if not self.current_scene:
                return False

            tag = self.current_scene.get_visual_tag(tag_id)
            if not tag:
                self.log.warning(f"Tag {tag_id} not found in current scene")
                return False

            # Check if position is being updated
            position_changed = False
            if "position" in updates or "transform" in updates:
                position_changed = True

            # Apply updates
            for key, value in updates.items():
                if hasattr(tag, key):
                    setattr(tag, key, value)
                else:
                    # Custom property
                    tag.properties[key] = value

            # Update spatial relationships if position changed (if spatial engine is available)
            if position_changed and self.spatial_engine:
                other_tags = [t for t in self.current_scene.visual_tags.values() if t.id != tag_id]
                self.spatial_engine.update_tag_spatial_relationships(tag, other_tags)

                # Update relationships for other tags as well
                for other_tag in other_tags:
                    self.spatial_engine.update_tag_spatial_relationships(other_tag, [tag] + [t for t in other_tags if t.id != other_tag.id])

            self.log.debug(f"Updated visual tag {tag_id}")
            self.events.publish("composer:tag_updated", scene_id=self.current_scene.id, tag_id=tag_id, updates=updates)

            return True

        except Exception as e:
            self.log.error(f"Failed to update visual tag: {e}")
            return False

    def update_tag_position(self, tag_id: str, x: float, y: float, z: float = None) -> bool:
        """Update tag position and recalculate spatial relationships"""
        try:
            if not self.current_scene:
                return False

            tag = self.current_scene.get_visual_tag(tag_id)
            if not tag:
                return False

            # Update position
            tag.transform.position.x = x
            tag.transform.position.y = y
            if z is not None:
                tag.transform.position.z = z

            # Update spatial relationships (if spatial engine is available)
            if self.spatial_engine:
                other_tags = [t for t in self.current_scene.visual_tags.values() if t.id != tag_id]
                self.spatial_engine.update_tag_spatial_relationships(tag, other_tags)

                # Update relationships for other affected tags
                for other_tag in other_tags:
                    self.spatial_engine.update_tag_spatial_relationships(other_tag, [tag] + [t for t in other_tags if t.id != other_tag.id])

            self.events.publish("composer:tag_moved", scene_id=self.current_scene.id, tag_id=tag_id, x=x, y=y, z=z)
            return True

        except Exception as e:
            self.log.error(f"Failed to update tag position: {e}")
            return False

    def remove_visual_tag(self, tag_id: str) -> bool:
        """Remove a visual tag from the current scene"""
        try:
            if not self.current_scene:
                return False

            success = self.current_scene.remove_visual_tag(tag_id)
            if success:
                self.log.debug(f"Removed visual tag {tag_id} from scene")
                self.events.publish("composer:tag_removed", scene_id=self.current_scene.id, tag_id=tag_id)

            return success

        except Exception as e:
            self.log.error(f"Failed to remove visual tag: {e}")
            return False

    def create_basic_tag(self, name: str, element_type: ElementType, position: tuple = (0, 0, 0)) -> VisualTag:
        """Create a basic visual tag with default settings"""
        from ..models.visual_tag import Transform, Vector3D

        tag = VisualTag(
            name=name,
            element_type=element_type,
            transform=Transform(position=Vector3D(*position))
        )

        # Set default profile based on element type
        if element_type == ElementType.CHARACTER:
            tag.primary_profile = AIProfile(DescriptorProfile.EMOTIONAL_EXPRESSIVE)
        elif element_type == ElementType.ENVIRONMENT:
            tag.primary_profile = AIProfile(DescriptorProfile.ATMOSPHERIC_MELLOW)
        elif element_type == ElementType.OBJECT:
            tag.primary_profile = AIProfile(DescriptorProfile.MATERIAL_STRUCTURAL)
        else:
            tag.primary_profile = AIProfile(DescriptorProfile.TECHNICAL_MECHANICAL)

        return tag

    def set_keyframe(self, tag_id: str, property_path: str, time: float, value) -> bool:
        """Set a keyframe for a tag property"""
        try:
            if not self.current_scene:
                return False

            tag = self.current_scene.get_visual_tag(tag_id)
            if not tag:
                self.log.warning(f"Tag {tag_id} not found")
                return False

            # Find or create animation curve for this property
            animation = None
            for anim in tag.animations:
                if anim.property_path == property_path:
                    animation = anim
                    break

            if not animation:
                # Create new animation curve
                from ..models.visual_tag import AnimationCurve, InterpolationType
                animation = AnimationCurve(
                    property_path=property_path,
                    interpolation=InterpolationType.LINEAR
                )
                tag.animations.append(animation)

            # Add or update keyframe
            from ..models.visual_tag import Keyframe
            existing_keyframe = None
            for kf in animation.keyframes:
                if abs(kf.time - time) < 0.001:  # Very close tolerance
                    existing_keyframe = kf
                    break

            if existing_keyframe:
                existing_keyframe.value = value
            else:
                keyframe = Keyframe(time=time, value=value)
                animation.keyframes.append(keyframe)
                # Sort keyframes by time
                animation.keyframes.sort(key=lambda k: k.time)

            self.log.debug(f"Set keyframe: {tag.name}.{property_path} = {value} at {time}s")
            self.events.publish("composer:keyframe_set", tag_id=tag_id, property=property_path, time=time, value=value)

            return True

        except Exception as e:
            self.log.error(f"Failed to set keyframe: {e}")
            return False

    def remove_keyframe(self, tag_id: str, property_path: str, time: float) -> bool:
        """Remove a keyframe from a tag property"""
        try:
            if not self.current_scene:
                return False

            tag = self.current_scene.get_visual_tag(tag_id)
            if not tag:
                return False

            # Find animation curve
            for animation in tag.animations:
                if animation.property_path == property_path:
                    # Find and remove keyframe
                    for i, keyframe in enumerate(animation.keyframes):
                        if abs(keyframe.time - time) < 0.001:
                            animation.keyframes.pop(i)
                            self.log.debug(f"Removed keyframe: {tag.name}.{property_path} at {time}s")
                            self.events.publish("composer:keyframe_removed", tag_id=tag_id, property=property_path, time=time)

                            # Remove animation if no keyframes left
                            if not animation.keyframes:
                                tag.animations.remove(animation)

                            return True
                    break

            return False

        except Exception as e:
            self.log.error(f"Failed to remove keyframe: {e}")
            return False

    def generate_prompt(self, time_segment: tuple = None) -> str:
        """Generate AI prompt for current scene or time segment"""
        try:
            if not self.current_scene:
                return ""

            scene = self.current_scene

            if time_segment:
                start_time, end_time = time_segment
                scene_at_time = scene.get_scene_at_time(start_time)
            else:
                scene_at_time = scene

            active_tags = scene_at_time.get_active_tags_at_time(scene_at_time.current_time)

            if not active_tags:
                return f"Empty scene: {scene.name}"

            # Analyze spatial relationships (if spatial engine is available)
            spatial_analyses = []
            if self.spatial_engine:
                spatial_analyses = self.spatial_engine.analyze_scene_spatial_relationships(active_tags)

            # Generate enhanced description with spatial intelligence
            descriptions = []

            # Start with basic tag descriptions
            for tag in active_tags:
                profile = tag.get_effective_profile()
                desc = f"A {tag.element_type.value}"
                if tag.name:
                    desc += f" named '{tag.name}'"

                # Add spatial context (if spatial engine is available)
                if self.spatial_engine:
                    spatial_desc = self.spatial_engine.generate_spatial_description(spatial_analyses, tag.id)
                    if spatial_desc:
                        desc += f" - {spatial_desc}"

                descriptions.append(desc)

            # Build comprehensive prompt
            prompt_parts = [f"Scene: {scene.name}"]

            if descriptions:
                prompt_parts.append("Elements: " + "; ".join(descriptions))

            # Add overall spatial composition
            if len(active_tags) > 1:
                overall_spatial = self._generate_overall_spatial_description(spatial_analyses)
                if overall_spatial:
                    prompt_parts.append(f"Composition: {overall_spatial}")

            prompt = ". ".join(prompt_parts) + "."

            self.log.debug(f"Generated enhanced prompt for scene '{scene.name}': {prompt[:100]}...")
            return prompt

        except Exception as e:
            self.log.error(f"Failed to generate prompt: {e}")
            return ""

    def _generate_overall_spatial_description(self, analyses) -> str:
        """Generate overall spatial composition description"""
        if not analyses:
            return ""

        # Count relationship types
        occlusion_count = len([a for a in analyses if a.occlusion_type.value != "no_occlusion"])
        high_confidence = [a for a in analyses if a.confidence > 0.7]

        parts = []
        if occlusion_count > 0:
            parts.append(f"Complex depth layering with {occlusion_count} occlusion relationships")
        if high_confidence:
            parts.append(f"{len(high_confidence)} precise spatial relationships")

        return ", ".join(parts) if parts else ""

    def export_to_generator(self, prompt: str = None) -> bool:
        """Export generated prompt to the video generator"""
        try:
            if not prompt:
                prompt = self.generate_prompt()

            if not prompt:
                self.log.warning("No prompt to export")
                return False

            # Check if Pixverse Generation plugin is available
            generator_service = self.framework.get_service("pixverse_service")
            if generator_service:
                # Direct integration with generator service would go here
                self.log.info("Direct generator integration not yet implemented")

            # Publish event for UI integration
            self.events.publish("composer:prompt_ready", {
                "prompt": prompt,
                "source": "visual_prompt_composer",
                "scene_id": self.current_scene.id if self.current_scene else None
            })

            self.log.info("Exported prompt to generator")
            return True

        except Exception as e:
            self.log.error(f"Failed to export to generator: {e}")
            return False

    def validate_current_scene(self) -> List[str]:
        """Validate the current scene for issues"""
        if not self.current_scene:
            return ["No current scene"]

        return self.current_scene.validate()

    def get_scene_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current scene"""
        if not self.current_scene:
            return {}

        scene = self.current_scene
        stats = {
            "name": scene.name,
            "duration": scene.duration,
            "tag_count": len(scene.visual_tags),
            "tag_types": {},
            "animated_tags": 0,
            "relationships_count": 0
        }

        # Count tags by type
        for tag in scene.visual_tags.values():
            tag_type = tag.element_type.value
            stats["tag_types"][tag_type] = stats["tag_types"].get(tag_type, 0) + 1

            if tag.animations:
                stats["animated_tags"] += 1

            stats["relationships_count"] += len(tag.spatial_relationships)

        return stats

    def shutdown(self):
        """Cleanup on service shutdown"""
        # Save current scene if it has unsaved changes
        if self.current_scene:
            try:
                # Auto-save to temporary location
                temp_save_dir = self.settings.resolve_user_path("temp_scenes")
                os.makedirs(temp_save_dir, exist_ok=True)
                temp_file = os.path.join(temp_save_dir, f"autosave_{self.current_scene.id}.json")
                self.current_scene.save_to_file(temp_file)
                self.log.info(f"Auto-saved current scene to {temp_file}")
            except Exception as e:
                self.log.error(f"Failed to auto-save scene: {e}")

        self.log.info("Visual Composer Service shut down")