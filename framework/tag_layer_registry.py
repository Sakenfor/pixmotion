from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from plugins.core.models import TagLayerDefinition, AssetTag

class TagLayerRegistry:
    """
    Registry for tag layers + persistence of layer definitions and asset tag values.
    Uses the main application's DatabaseService and SQLAlchemy ORM.
    """
    def __init__(self, framework):
        self._db = framework.get_service("database_service")
        self._log = framework.get_service("log_manager")

    def _get_session(self) -> Session:
        return self._db.get_session()

    def list_layers(self) -> List[Dict[str, Any]]:
        session = self._get_session()
        try:
            # Check if table exists before querying
            from sqlalchemy import inspect
            inspector = inspect(session.bind)
            if 'tag_layer_definitions' not in inspector.get_table_names():
                self._log.warning("Tag layer definitions table does not exist yet")
                return []

            layers = session.query(TagLayerDefinition).order_by(TagLayerDefinition.id).all()
            return [layer.to_dict() for layer in layers]
        except Exception as e:
            self._log.error(f"Error listing tag layers: {e}")
            return []
        finally:
            session.close()

    def get_layer(self, layer_id: str) -> Optional[Dict[str, Any]]:
        session = self._get_session()
        try:
            layer = session.query(TagLayerDefinition).filter_by(id=layer_id).one_or_none()
            return layer.to_dict() if layer else None
        finally:
            session.close()

    def upsert_layer(self, layer_data: Dict[str, Any]) -> None:
        session = self._get_session()
        try:
            # Check if table exists before querying
            from sqlalchemy import inspect
            inspector = inspect(session.bind)
            if 'tag_layer_definitions' not in inspector.get_table_names():
                self._log.warning(f"Tag layer definitions table does not exist yet, cannot upsert layer {layer_data.get('id', 'unknown')}")
                return

            layer_id = layer_data.get("id")
            if not layer_id:
                self._log.error("Cannot upsert layer without an 'id'.")
                return
            layer = session.query(TagLayerDefinition).filter_by(id=layer_id).one_or_none()
            if layer is None:
                layer = TagLayerDefinition(**layer_data)
                session.add(layer)
            else:
                for key, value in layer_data.items():
                    setattr(layer, key, value)
            session.commit()
        except Exception as e:
            session.rollback()
            self._log.error(f"Failed to upsert layer {layer_data.get('id', 'unknown')}: {e}", exc_info=True)
        finally:
            session.close()

    def delete_layer(self, layer_id: str) -> None:
        session = self._get_session()
        try:
            layer = session.query(TagLayerDefinition).filter_by(id=layer_id).one_or_none()
            if layer:
                session.delete(layer)
                session.commit()
        except Exception as e:
            session.rollback()
            self._log.error(f"Failed to delete layer {layer_id}: {e}", exc_info=True)
        finally:
            session.close()

    def add_tags(self, *, asset_id: str, layer_id: str, values: List[Dict[str, Any]], source: str = "AI") -> None:
        session = self._get_session()
        try:
            layer_def = session.query(TagLayerDefinition).filter_by(id=layer_id).one_or_none()
            if layer_def and not layer_def.multi_select:
                session.query(AssetTag).filter_by(asset_id=asset_id, layer_id=layer_id, source="AI").delete()

            for v in values:
                tag_data = {"asset_id": asset_id, "layer_id": layer_id, "source": source, "value": v.get("value"),
                            "numeric_value": v.get("numeric_value"), "text_value": v.get("text_value"),
                            "embedding": v.get("embedding"), "confidence": v.get("confidence"),
                            "analysis_version": v.get("analysis_version")}
                session.merge(AssetTag(**{k: v for k, v in tag_data.items() if v is not None}))
            session.commit()
        except Exception as e:
            session.rollback()
            self._log.error(f"Failed to add tags for asset {asset_id}: {e}", exc_info=True)
        finally:
            session.close()

    def list_asset_tags(self, asset_id: str) -> List[Dict[str, Any]]:
        session = self._get_session()
        try:
            tags = session.query(AssetTag).filter_by(asset_id=asset_id).all()
            return [{"layer_id": tag.layer_id, "value": tag.value, "numeric_value": tag.numeric_value,
                     "text_value": tag.text_value, "confidence": tag.confidence, "source": tag.source} for tag in tags]
        finally:
            session.close()

    def ensure_default_layers(self):
        """Create default layers if none exist - safe to call after database initialization"""
        try:
            # Check if we already have layers
            if self.list_layers():
                self._log.info("Tag layers already exist, skipping default layer creation")
                return

            # Create default layers
            self._create_default_layers()
        except Exception as e:
            self._log.error(f"Failed to ensure default layers: {e}", exc_info=True)

    def _create_default_layers(self):
        """Create the default AI tag layers"""
        # Light/Fast AI tags for filtering
        self.upsert_layer({
            "id": "basic_content", "name": "Basic Content",
            "description": "Fast content classification for filtering",
            "multi_select": True, "stage": "quick", "value_type": "categorical",
            "processing_priority": 1, "ai_provider": "offline", "enabled": True,
            "prompt": "Classify this image/video into basic categories: person, object, landscape, text, abstract, animal",
            "engine": {"model": "clip-vit-base"},
            "hierarchy": {
                "person": ["human", "character"],
                "object": ["furniture", "vehicle", "tool", "clothing"],
                "landscape": ["indoor", "outdoor", "urban", "nature"]
            }
        })

        self.upsert_layer({
            "id": "nsfw_filter", "name": "Content Safety",
            "description": "NSFW content detection for safe filtering",
            "multi_select": False, "stage": "quick", "value_type": "numeric",
            "processing_priority": 1, "ai_provider": "offline", "enabled": True,
            "prompt": "Rate the NSFW content level from 0.0 (safe) to 1.0 (explicit)",
            "engine": {"model": "nsfw-detector"}
        })

        self.upsert_layer({
            "id": "color_dominant", "name": "Dominant Colors",
            "description": "Primary color palette for visual filtering",
            "multi_select": True, "stage": "quick", "value_type": "categorical",
            "processing_priority": 1, "ai_provider": "offline", "enabled": True,
            "prompt": "Identify the dominant colors in this image: red, blue, green, yellow, orange, purple, pink, brown, black, white, gray",
            "engine": {"model": "color-classifier"}
        })

        # Advanced AI tags for gameplay organization
        self.upsert_layer({
            "id": "emotion_detailed", "name": "Detailed Emotions",
            "description": "Complex emotional analysis for gameplay scenarios",
            "multi_select": True, "stage": "deep", "value_type": "categorical",
            "processing_priority": 3, "ai_provider": "default", "enabled": True,
            "prompt": "Analyze the emotional content and mood of this image. Identify specific emotions, expressions, and emotional atmosphere that would be useful for storytelling and gameplay scenarios.",
            "engine": {"model": "gpt-4-vision-preview"},
            "hierarchy": {
                "positive": ["joy", "excitement", "calm", "confident", "romantic", "playful"],
                "negative": ["sadness", "anger", "fear", "disgust", "anxiety", "loneliness"],
                "complex": ["nostalgic", "mysterious", "dramatic", "intense", "serene", "chaotic"]
            }
        })

        self.upsert_layer({
            "id": "clothing_style", "name": "Clothing & Fashion",
            "description": "Detailed clothing and style analysis for character customization",
            "multi_select": True, "stage": "deep", "value_type": "categorical",
            "processing_priority": 2, "ai_provider": "default", "enabled": True,
            "prompt": "Identify and describe clothing items, fashion styles, and accessories visible in this image. Focus on: clothing types, colors, styles, era, formality level.",
            "engine": {"model": "gpt-4-vision-preview"},
            "hierarchy": {
                "clothing": ["shirt", "dress", "pants", "skirt", "jacket", "sweater", "suit"],
                "style": ["casual", "formal", "vintage", "modern", "punk", "gothic", "bohemian"],
                "accessories": ["jewelry", "hat", "glasses", "bag", "shoes", "watch"]
            }
        })

        self.upsert_layer({
            "id": "scene_context", "name": "Scene Context",
            "description": "Environmental context and setting analysis for world-building",
            "multi_select": True, "stage": "deep", "value_type": "categorical",
            "processing_priority": 3, "ai_provider": "default", "enabled": True,
            "prompt": "Analyze the setting, environment, and context of this scene. Describe: location type, time period, atmosphere, activities happening, objects present that tell a story.",
            "engine": {"model": "gpt-4-vision-preview"},
            "hierarchy": {
                "location": ["indoor", "outdoor", "urban", "rural", "fantasy", "sci-fi"],
                "time": ["modern", "historical", "futuristic", "timeless"],
                "mood": ["peaceful", "busy", "abandoned", "luxurious", "simple", "chaotic"]
            }
        })

        self._log.info("Created 6 default AI tag layers successfully")
