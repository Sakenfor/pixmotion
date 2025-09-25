"""
Spatial Intelligence Engine

Advanced spatial analysis system for detecting occlusion, depth relationships,
and generating precise spatial descriptions for visual prompt composition.
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import math
import numpy as np

from interfaces import IService
from ..models.visual_tag import VisualTag, ElementType, Vector3D, SpatialRelationship, RelationType


class OcclusionType(Enum):
    """Types of occlusion relationships"""
    FULLY_HIDDEN = "fully_hidden"
    PARTIALLY_HIDDEN = "partially_hidden"
    EDGE_OCCLUDED = "edge_occluded"
    NO_OCCLUSION = "no_occlusion"


class SpatialZone(Enum):
    """Spatial zones for relative positioning"""
    FOREGROUND = "foreground"
    MIDDLE_GROUND = "middle_ground"
    BACKGROUND = "background"
    TOUCHING = "touching"
    OVERLAPPING = "overlapping"
    INSIDE = "inside"
    SURROUNDING = "surrounding"


@dataclass
class SpatialAnalysis:
    """Result of spatial relationship analysis"""
    tag_id: str
    related_tag_id: str
    occlusion_type: OcclusionType
    spatial_zone: SpatialZone
    distance: float
    depth_difference: float
    angle: float  # relative angle in degrees
    confidence: float  # analysis confidence 0.0-1.0
    description_fragments: List[str]


class SpatialIntelligenceEngine(IService):
    """Advanced spatial analysis and description generation service"""

    def initialize(self):
        """Initialize the spatial intelligence engine"""
        self.log = self.framework.get_service("log_manager")
        self.events = self.framework.get_service("event_manager")

        # Analysis parameters
        self.occlusion_threshold = 0.1  # minimum overlap for occlusion detection
        self.depth_sensitivity = 0.05   # minimum depth difference to consider
        self.proximity_threshold = 100  # distance threshold for "near" relationships

        # Spatial description templates
        self._init_description_templates()

        self.log.info("Spatial Intelligence Engine initialized")

    def _init_description_templates(self):
        """Initialize spatial description templates"""
        self.occlusion_templates = {
            OcclusionType.FULLY_HIDDEN: [
                "{object} is completely hidden behind {occluder}",
                "{occluder} completely obscures {object}",
                "{object} is fully blocked from view by {occluder}"
            ],
            OcclusionType.PARTIALLY_HIDDEN: [
                "{object} is partially hidden behind {occluder}",
                "{occluder} partially obscures {object}",
                "Part of {object} is blocked by {occluder}",
                "{object} emerges from behind {occluder}"
            ],
            OcclusionType.EDGE_OCCLUDED: [
                "{object} is slightly obscured by {occluder}",
                "The edge of {object} is hidden by {occluder}",
                "{occluder} clips the edge of {object}"
            ]
        }

        self.spatial_templates = {
            SpatialZone.FOREGROUND: [
                "{object} is prominently in the foreground",
                "{object} dominates the front of the scene",
                "{object} is closest to the viewer"
            ],
            SpatialZone.MIDDLE_GROUND: [
                "{object} occupies the middle distance",
                "{object} is positioned in the middle ground",
                "{object} sits at medium depth"
            ],
            SpatialZone.BACKGROUND: [
                "{object} recedes into the background",
                "{object} is distant in the background",
                "{object} forms part of the far scenery"
            ],
            SpatialZone.TOUCHING: [
                "{object} is touching {related}",
                "{object} makes contact with {related}",
                "{object} and {related} are pressed together"
            ],
            SpatialZone.OVERLAPPING: [
                "{object} overlaps with {related}",
                "{object} and {related} intersect",
                "{object} crosses over {related}"
            ],
            SpatialZone.INSIDE: [
                "{object} is inside {related}",
                "{object} is contained within {related}",
                "{related} encloses {object}"
            ],
            SpatialZone.SURROUNDING: [
                "{object} surrounds {related}",
                "{object} encircles {related}",
                "{related} is surrounded by {object}"
            ]
        }

    def analyze_scene_spatial_relationships(self, visual_tags: List[VisualTag]) -> List[SpatialAnalysis]:
        """Analyze spatial relationships between all tags in a scene"""
        analyses = []

        for i, tag in enumerate(visual_tags):
            for j, other_tag in enumerate(visual_tags):
                if i != j:
                    analysis = self._analyze_pair_relationship(tag, other_tag)
                    if analysis and analysis.confidence > 0.3:  # Only keep meaningful relationships
                        analyses.append(analysis)

        return analyses

    def _analyze_pair_relationship(self, tag1: VisualTag, tag2: VisualTag) -> Optional[SpatialAnalysis]:
        """Analyze spatial relationship between two specific tags"""
        try:
            # Calculate basic spatial metrics
            distance = self._calculate_2d_distance(tag1.transform.position, tag2.transform.position)
            depth_diff = tag2.transform.position.z - tag1.transform.position.z
            angle = self._calculate_relative_angle(tag1.transform.position, tag2.transform.position)

            # Determine occlusion type
            occlusion = self._analyze_occlusion(tag1, tag2, depth_diff)

            # Determine spatial zone relationship
            spatial_zone = self._determine_spatial_zone(tag1, tag2, distance, depth_diff)

            # Calculate confidence based on various factors
            confidence = self._calculate_relationship_confidence(tag1, tag2, distance, depth_diff, occlusion)

            # Generate description fragments
            description_fragments = self._generate_description_fragments(
                tag1, tag2, occlusion, spatial_zone, distance, depth_diff
            )

            return SpatialAnalysis(
                tag_id=tag1.id,
                related_tag_id=tag2.id,
                occlusion_type=occlusion,
                spatial_zone=spatial_zone,
                distance=distance,
                depth_difference=depth_diff,
                angle=angle,
                confidence=confidence,
                description_fragments=description_fragments
            )

        except Exception as e:
            self.log.error(f"Failed to analyze relationship between {tag1.name} and {tag2.name}: {e}")
            return None

    def _calculate_2d_distance(self, pos1: Vector3D, pos2: Vector3D) -> float:
        """Calculate 2D distance ignoring Z depth"""
        return math.sqrt((pos2.x - pos1.x)**2 + (pos2.y - pos1.y)**2)

    def _calculate_relative_angle(self, pos1: Vector3D, pos2: Vector3D) -> float:
        """Calculate angle from pos1 to pos2 in degrees"""
        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        return math.degrees(math.atan2(dy, dx))

    def _analyze_occlusion(self, tag1: VisualTag, tag2: VisualTag, depth_diff: float) -> OcclusionType:
        """Analyze occlusion relationship between two tags"""
        # Only consider occlusion if there's meaningful depth difference
        if abs(depth_diff) < self.depth_sensitivity:
            return OcclusionType.NO_OCCLUSION

        # Calculate 2D overlap
        overlap = self._calculate_2d_overlap(tag1, tag2)

        if overlap > 0.8:  # High overlap
            return OcclusionType.FULLY_HIDDEN if depth_diff > 0 else OcclusionType.NO_OCCLUSION
        elif overlap > 0.3:  # Moderate overlap
            return OcclusionType.PARTIALLY_HIDDEN if depth_diff > 0 else OcclusionType.NO_OCCLUSION
        elif overlap > 0.1:  # Light overlap
            return OcclusionType.EDGE_OCCLUDED if depth_diff > 0 else OcclusionType.NO_OCCLUSION
        else:
            return OcclusionType.NO_OCCLUSION

    def _calculate_2d_overlap(self, tag1: VisualTag, tag2: VisualTag) -> float:
        """Calculate 2D overlap ratio between two tags (simplified bounding box approach)"""
        # For now, use simplified circular overlap calculation
        # In a full implementation, this would use actual tag shapes/bounds

        distance = self._calculate_2d_distance(tag1.transform.position, tag2.transform.position)

        # Assume default radius based on tag type
        radius1 = self._get_tag_radius(tag1)
        radius2 = self._get_tag_radius(tag2)

        # Calculate overlap using circle intersection
        if distance >= radius1 + radius2:
            return 0.0  # No overlap
        elif distance <= abs(radius1 - radius2):
            return 1.0  # Complete overlap
        else:
            # Partial overlap calculation (simplified)
            overlap_distance = radius1 + radius2 - distance
            max_overlap = min(radius1, radius2) * 2
            return overlap_distance / max_overlap

    def _get_tag_radius(self, tag: VisualTag) -> float:
        """Get approximate radius for a tag based on its type"""
        radius_map = {
            ElementType.CHARACTER: 40,
            ElementType.OBJECT: 30,
            ElementType.ENVIRONMENT: 60,
            ElementType.LIGHT: 20,
            ElementType.CAMERA: 25,
            ElementType.EFFECT: 35
        }
        return radius_map.get(tag.element_type, 30)

    def _determine_spatial_zone(self, tag1: VisualTag, tag2: VisualTag, distance: float, depth_diff: float) -> SpatialZone:
        """Determine the spatial zone relationship between tags"""
        # Check for containment relationships first
        if self._is_tag_inside(tag1, tag2):
            return SpatialZone.INSIDE
        elif self._is_tag_inside(tag2, tag1):
            return SpatialZone.SURROUNDING

        # Check for proximity relationships
        if distance < 10:  # Very close
            return SpatialZone.TOUCHING
        elif distance < 50 and abs(depth_diff) < 5:
            return SpatialZone.OVERLAPPING

        # Depth-based relationships
        if abs(depth_diff) > 100:
            if depth_diff > 0:
                return SpatialZone.BACKGROUND  # tag2 is in background relative to tag1
            else:
                return SpatialZone.FOREGROUND  # tag2 is in foreground relative to tag1

        return SpatialZone.MIDDLE_GROUND

    def _is_tag_inside(self, inner_tag: VisualTag, outer_tag: VisualTag) -> bool:
        """Check if one tag is inside another (simplified)"""
        # This would be more complex in a full implementation
        # For now, check if inner tag is very close and outer tag is much larger
        distance = self._calculate_2d_distance(inner_tag.transform.position, outer_tag.transform.position)
        inner_radius = self._get_tag_radius(inner_tag)
        outer_radius = self._get_tag_radius(outer_tag)

        return distance + inner_radius < outer_radius * 0.8

    def _calculate_relationship_confidence(self, tag1: VisualTag, tag2: VisualTag,
                                         distance: float, depth_diff: float,
                                         occlusion: OcclusionType) -> float:
        """Calculate confidence score for the spatial relationship analysis"""
        confidence = 0.5  # Base confidence

        # Higher confidence for closer objects
        if distance < self.proximity_threshold:
            confidence += 0.2

        # Higher confidence for significant depth differences
        if abs(depth_diff) > self.depth_sensitivity * 10:
            confidence += 0.2

        # Higher confidence for clear occlusion relationships
        if occlusion != OcclusionType.NO_OCCLUSION:
            confidence += 0.3

        # Lower confidence for very distant objects
        if distance > 500:
            confidence -= 0.3

        return max(0.0, min(1.0, confidence))

    def _generate_description_fragments(self, tag1: VisualTag, tag2: VisualTag,
                                      occlusion: OcclusionType, spatial_zone: SpatialZone,
                                      distance: float, depth_diff: float) -> List[str]:
        """Generate descriptive text fragments for the spatial relationship"""
        fragments = []

        # Add occlusion descriptions
        if occlusion != OcclusionType.NO_OCCLUSION:
            templates = self.occlusion_templates[occlusion]
            if templates:
                template = templates[0]  # Use first template for now
                fragment = template.format(object=tag1.name or f"the {tag1.element_type.value}",
                                         occluder=tag2.name or f"the {tag2.element_type.value}")
                fragments.append(fragment)

        # Add spatial zone descriptions
        if spatial_zone in self.spatial_templates:
            templates = self.spatial_templates[spatial_zone]
            if templates:
                template = templates[0]  # Use first template for now
                if spatial_zone in [SpatialZone.TOUCHING, SpatialZone.OVERLAPPING,
                                   SpatialZone.INSIDE, SpatialZone.SURROUNDING]:
                    fragment = template.format(object=tag1.name or f"the {tag1.element_type.value}",
                                             related=tag2.name or f"the {tag2.element_type.value}")
                else:
                    fragment = template.format(object=tag1.name or f"the {tag1.element_type.value}")
                fragments.append(fragment)

        # Add distance-based descriptions
        if distance < 20:
            fragments.append(f"very close to {tag2.name or f'the {tag2.element_type.value}'}")
        elif distance > 300:
            fragments.append(f"far from {tag2.name or f'the {tag2.element_type.value}'}")

        return fragments

    def generate_spatial_description(self, analyses: List[SpatialAnalysis],
                                   primary_tag_id: str = None) -> str:
        """Generate comprehensive spatial description from analyses"""
        if not analyses:
            return ""

        # Group analyses by primary tag if specified
        if primary_tag_id:
            relevant_analyses = [a for a in analyses if a.tag_id == primary_tag_id]
        else:
            relevant_analyses = analyses

        # Sort by confidence
        relevant_analyses.sort(key=lambda x: x.confidence, reverse=True)

        # Build description
        descriptions = []
        for analysis in relevant_analyses[:3]:  # Take top 3 relationships
            if analysis.description_fragments:
                descriptions.extend(analysis.description_fragments[:2])  # Take top 2 fragments per analysis

        if descriptions:
            return ". ".join(descriptions) + "."
        else:
            return ""

    def update_tag_spatial_relationships(self, tag: VisualTag, other_tags: List[VisualTag]):
        """Update spatial relationships for a specific tag"""
        try:
            tag.spatial_relationships.clear()

            for other_tag in other_tags:
                if other_tag.id != tag.id:
                    analysis = self._analyze_pair_relationship(tag, other_tag)
                    if analysis and analysis.confidence > 0.4:
                        # Convert to SpatialRelationship model
                        relationship = SpatialRelationship(
                            target_tag_id=other_tag.id,
                            relation_type=self._map_to_relation_type(analysis.spatial_zone, analysis.occlusion_type),
                            distance=analysis.distance,
                            confidence=analysis.confidence
                        )
                        tag.spatial_relationships.append(relationship)

            self.log.debug(f"Updated spatial relationships for {tag.name}: {len(tag.spatial_relationships)} relationships")

        except Exception as e:
            self.log.error(f"Failed to update spatial relationships for {tag.name}: {e}")

    def _map_to_relation_type(self, spatial_zone: SpatialZone, occlusion: OcclusionType) -> RelationType:
        """Map spatial analysis results to RelationType enum"""
        if occlusion == OcclusionType.FULLY_HIDDEN:
            return RelationType.BEHIND
        elif occlusion == OcclusionType.PARTIALLY_HIDDEN:
            return RelationType.PARTIALLY_BEHIND
        elif spatial_zone == SpatialZone.TOUCHING:
            return RelationType.ADJACENT
        elif spatial_zone == SpatialZone.INSIDE:
            return RelationType.INSIDE
        elif spatial_zone == SpatialZone.SURROUNDING:
            return RelationType.CONTAINS
        elif spatial_zone == SpatialZone.FOREGROUND:
            return RelationType.IN_FRONT
        else:
            return RelationType.NEAR

    def shutdown(self):
        """Cleanup on service shutdown"""
        self.log.info("Spatial Intelligence Engine shut down")