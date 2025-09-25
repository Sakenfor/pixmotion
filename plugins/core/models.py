# story_studio_project/plugins/core/models.py
import datetime
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Float,
    UniqueConstraint,
    Enum as SQLAlchemyEnum,
    Boolean,
    BLOB
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class AssetType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"

class Asset(Base):
    __tablename__ = "assets"
    id = Column(String(64), primary_key=True, unique=True, nullable=False)
    path = Column(String(1024), unique=True, nullable=False)
    asset_type = Column(SQLAlchemyEnum(AssetType, name="asset_type_enum"), nullable=False)
    thumbnail_path = Column(String(1024))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    rating = Column(Integer, default=0, nullable=False)

    tags = relationship("AssetTag", back_populates="asset", cascade="all, delete-orphan")
    generations_as_input1 = relationship("Generation", foreign_keys="[Generation.input_asset1_id]", back_populates="input_asset1")
    generations_as_input2 = relationship("Generation", foreign_keys="[Generation.input_asset2_id]", back_populates="input_asset2")
    generation_as_output = relationship("Generation", foreign_keys="[Generation.output_asset_id]", back_populates="output_asset")
    emotion_clips = relationship("EmotionClip", back_populates="asset", cascade="all, delete-orphan")

class Generation(Base):
    __tablename__ = "generations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(String(2048), nullable=False)
    input_asset1_id = Column(String(64), ForeignKey("assets.id"), nullable=False)
    input_asset2_id = Column(String(64), ForeignKey("assets.id"), nullable=True)
    output_asset_id = Column(String(64), ForeignKey("assets.id"), unique=True, nullable=False)
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    input_asset1 = relationship("Asset", foreign_keys=[input_asset1_id], back_populates="generations_as_input1")
    input_asset2 = relationship("Asset", foreign_keys=[input_asset2_id], back_populates="generations_as_input2")
    output_asset = relationship("Asset", foreign_keys=[output_asset_id], back_populates="generation_as_output")

class EmotionClip(Base):
    __tablename__ = "emotion_clips"
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(64), ForeignKey("assets.id"), nullable=False)
    package_uuid = Column(String(64), nullable=False)
    intent = Column(String(128), nullable=False)
    # ... other columns
    __table_args__ = (UniqueConstraint("asset_id", "package_uuid", "intent", name="uq_emotion_clip"),)
    asset = relationship("Asset", back_populates="emotion_clips")


class TagLayerDefinition(Base):
    __tablename__ = "tag_layer_definitions"
    id = Column(String(128), primary_key=True)
    name = Column(String(256), nullable=False)
    description = Column(String, default="")
    multi_select = Column(Boolean, default=True)
    stage = Column(String(64), default="quick")  # "quick", "deep", "manual"
    value_type = Column(String(64), default="categorical")  # "categorical", "numeric", "text", "embedding"
    engine = Column(JSON, default=lambda: {})
    hierarchy = Column(JSON, default=lambda: {})
    prompt = Column(String(2048), default="")  # Custom scanning prompt for this layer
    ai_provider = Column(String(64), default="default")  # "openai", "anthropic", "local", "offline"
    processing_priority = Column(Integer, default=1)  # 1=light/fast, 2=medium, 3=deep/slow
    enabled = Column(Boolean, default=True)
    tags = relationship("AssetTag", back_populates="layer", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description, "multi_select": self.multi_select,
                "stage": self.stage, "value_type": self.value_type, "engine": self.engine, "hierarchy": self.hierarchy,
                "prompt": self.prompt, "ai_provider": self.ai_provider, "processing_priority": self.processing_priority,
                "enabled": self.enabled}

class AssetTag(Base):
    __tablename__ = "asset_tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(64), ForeignKey("assets.id"), nullable=False, index=True)
    layer_id = Column(String(128), ForeignKey("tag_layer_definitions.id"), nullable=False, index=True)
    value = Column(String(256))
    numeric_value = Column(Float)
    text_value = Column(String)
    embedding = Column(BLOB)
    confidence = Column(Float)
    source = Column(String(64), default="AI")
    analysis_version = Column(String(32))
    asset = relationship("Asset", back_populates="tags")
    layer = relationship("TagLayerDefinition", back_populates="tags")
    __table_args__ = (UniqueConstraint('asset_id', 'layer_id', 'value', name='_asset_layer_value_uc'),)
