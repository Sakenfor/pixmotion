# story_studio_project/plugins/core/models.py
import datetime
import enum
from sqlalchemy import (Column, Integer, String, DateTime,
                        ForeignKey, JSON, Enum as SQLAlchemyEnum)
from sqlalchemy.orm import relationship, declarative_base

# This Base is the single, shared foundation for all database models
# across all plugins. Any plugin can import and inherit from this Base.
Base = declarative_base()


class AssetType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class Asset(Base):
    __tablename__ = 'assets'
    id = Column(String(64), primary_key=True, unique=True, nullable=False)
    path = Column(String(1024), unique=True, nullable=False)
    asset_type = Column(SQLAlchemyEnum(AssetType, name="asset_type_enum"), nullable=False)
    thumbnail_path = Column(String(1024))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    rating = Column(Integer, default=0, nullable=False)
    generations_as_input1 = relationship("Generation", foreign_keys="[Generation.input_asset1_id]",
                                         back_populates="input_asset1")
    generations_as_input2 = relationship("Generation", foreign_keys="[Generation.input_asset2_id]",
                                         back_populates="input_asset2")
    generation_as_output = relationship("Generation", foreign_keys="[Generation.output_asset_id]",
                                        back_populates="output_asset")


class Generation(Base):
    __tablename__ = 'generations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(String(2048), nullable=False)
    input_asset1_id = Column(String(64), ForeignKey('assets.id'), nullable=False)
    input_asset2_id = Column(String(64), ForeignKey('assets.id'), nullable=True)
    output_asset_id = Column(String(64), ForeignKey('assets.id'), unique=True, nullable=False)
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    input_asset1 = relationship("Asset", foreign_keys=[input_asset1_id], back_populates="generations_as_input1")
    input_asset2 = relationship("Asset", foreign_keys=[input_asset2_id], back_populates="generations_as_input2")
    output_asset = relationship("Asset", foreign_keys=[output_asset_id], back_populates="generation_as_output")
