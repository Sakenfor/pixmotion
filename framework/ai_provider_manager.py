from __future__ import annotations
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class AIProviderConfig:
    """Configuration for an AI provider"""
    id: str
    name: str
    type: str  # "api", "local", "offline"
    enabled: bool = True
    settings: Dict[str, Any] = None
    supported_models: List[str] = None

    def __post_init__(self):
        if self.settings is None:
            self.settings = {}
        if self.supported_models is None:
            self.supported_models = []

class AIProviderManager:
    """
    Manages AI provider configurations and model selection for tag layer processing.
    Supports API services (OpenAI, Anthropic), local models, and offline processing.
    """

    def __init__(self, framework):
        self.framework = framework
        self.settings = framework.get_service("settings_service")
        self.log = framework.get_service("log_manager")
        self._providers = {}
        self._load_default_providers()

    def _load_default_providers(self):
        """Load default AI provider configurations"""
        defaults = {
            "openai": AIProviderConfig(
                id="openai",
                name="OpenAI GPT Vision",
                type="api",
                enabled=False,
                settings={
                    "api_key": "",
                    "model": "gpt-4-vision-preview",
                    "max_tokens": 300,
                    "temperature": 0.1
                },
                supported_models=["gpt-4-vision-preview", "gpt-4o", "gpt-4o-mini"]
            ),
            "anthropic": AIProviderConfig(
                id="anthropic",
                name="Anthropic Claude Vision",
                type="api",
                enabled=False,
                settings={
                    "api_key": "",
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 300
                },
                supported_models=["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
            ),
            "local_llama": AIProviderConfig(
                id="local_llama",
                name="Local LLaMA Vision",
                type="local",
                enabled=False,
                settings={
                    "model_path": "",
                    "gpu_enabled": True,
                    "context_length": 2048
                },
                supported_models=["llava-1.6-vicuna-7b", "llava-1.6-vicuna-13b"]
            ),
            "offline": AIProviderConfig(
                id="offline",
                name="Offline Classification",
                type="offline",
                enabled=True,
                settings={
                    "models_dir": "models/",
                    "batch_size": 32
                },
                supported_models=["clip-vit-base", "emotion-classifier", "nsfw-detector"]
            )
        }

        # Load saved provider configs or use defaults
        saved_providers = self.settings.get("ai_providers", {})
        for provider_id, default_config in defaults.items():
            if provider_id in saved_providers:
                # Update with saved settings but preserve structure
                saved = saved_providers[provider_id]
                default_config.enabled = saved.get("enabled", default_config.enabled)
                default_config.settings.update(saved.get("settings", {}))
            self._providers[provider_id] = default_config

    def get_provider(self, provider_id: str) -> Optional[AIProviderConfig]:
        """Get a specific AI provider configuration"""
        return self._providers.get(provider_id)

    def list_providers(self) -> List[AIProviderConfig]:
        """List all available AI providers"""
        return list(self._providers.values())

    def list_enabled_providers(self) -> List[AIProviderConfig]:
        """List only enabled AI providers"""
        return [p for p in self._providers.values() if p.enabled]

    def update_provider(self, provider_id: str, settings: Dict[str, Any]) -> bool:
        """Update provider settings"""
        if provider_id not in self._providers:
            return False

        provider = self._providers[provider_id]
        provider.enabled = settings.get("enabled", provider.enabled)
        provider.settings.update(settings.get("settings", {}))

        # Save to persistent settings
        self._save_providers()
        return True

    def get_best_provider_for_layer(self, layer_config: Dict[str, Any]) -> Optional[AIProviderConfig]:
        """Get the best AI provider for a given tag layer configuration"""
        preferred_provider = layer_config.get("ai_provider", "default")
        processing_priority = layer_config.get("processing_priority", 1)

        # If specific provider requested and available
        if preferred_provider != "default" and preferred_provider in self._providers:
            provider = self._providers[preferred_provider]
            if provider.enabled:
                return provider

        # Auto-select based on processing priority
        enabled_providers = self.list_enabled_providers()

        if processing_priority == 1:  # Light/fast processing
            # Prefer offline > local > API for speed
            for provider_type in ["offline", "local", "api"]:
                for provider in enabled_providers:
                    if provider.type == provider_type:
                        return provider

        elif processing_priority == 3:  # Deep/slow processing
            # Prefer API > local > offline for quality
            for provider_type in ["api", "local", "offline"]:
                for provider in enabled_providers:
                    if provider.type == provider_type:
                        return provider

        else:  # Medium processing
            # Balanced preference: local > API > offline
            for provider_type in ["local", "api", "offline"]:
                for provider in enabled_providers:
                    if provider.type == provider_type:
                        return provider

        return enabled_providers[0] if enabled_providers else None

    def _save_providers(self):
        """Save provider configurations to settings"""
        providers_data = {}
        for provider_id, provider in self._providers.items():
            providers_data[provider_id] = {
                "enabled": provider.enabled,
                "settings": provider.settings
            }
        self.settings.set("ai_providers", providers_data)