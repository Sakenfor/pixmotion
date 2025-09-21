"""Compatibility module re-exporting asset models from the core plugin."""

from plugins.core.models import (
    Asset as CoreAsset,
    AssetType as CoreAssetType,
    EmotionClip as CoreEmotionClip,
)

Asset = CoreAsset
AssetType = CoreAssetType
EmotionClip = CoreEmotionClip

__all__ = ["Asset", "AssetType", "EmotionClip"]
