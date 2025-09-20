# story_studio_project/plugins/assets/models.py
import datetime
import enum
from sqlalchemy import (Column, Integer, String, DateTime,
                        ForeignKey, JSON, Enum as SQLAlchemyEnum)
from sqlalchemy.orm import relationship

# Import the shared Base from the core plugin
from core.models import Base

class AssetType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"

class Asset(Base):
    """
    This model is now defined within the 'assets' plugin,
    but it inherits from the core's shared Base, so it will be part
    of the same database and metadata collection.
    """
    __tablename__ = 'assets'
    id = Column(String(64), primary_key=True, unique=True, nullable=False)
    path = Column(String(1024), unique=True, nullable=False)
    asset_type = Column(SQLAlchemyEnum(AssetType, name="asset_type_enum"), nullable=False)
    thumbnail_path = Column(String(1024))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    rating = Column(Integer, default=0, nullable=False)

    # Note: Relationships to models in other plugins (like Generation)
    # can still be defined here as strings.
    generations_as_input1 = relationship("Generation", foreign_keys="[Generation.input_asset1_id]",
                                         back_populates="input_asset1")
    generations_as_input2 = relationship("Generation", foreign_keys="[Generation.input_asset2_id]",
                                         back_populates="input_asset2")
    generation_as_output = relationship("Generation", foreign_keys="[Generation.output_asset_id]",
                                        back_populates="output_asset")
