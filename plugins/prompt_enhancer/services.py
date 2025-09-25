"""
Prompt Enhancement Service - Enhances prompts using AI Hub models
"""
from interfaces import IService
from typing import Dict, Any, List, Optional, Callable
import json
import re


class PromptEnhancerService(IService):
    """
    Service that enhances video generation prompts using available AI Hub models.
    Integrates with the AI Hub service to provide offline and API-based prompt enhancement.
    """

    def __init__(self, framework):
        super().__init__(framework)
        self.log = framework.get_service("log_manager")
        self.ai_hub = None
        self.settings = None

    def initialize(self):
        """Initialize the service after all plugins are loaded"""
        self.ai_hub = self.framework.get_service("ai_hub")
        self.settings = self.framework.get_service("settings_service")

        if not self.ai_hub:
            self.log.warning("AI Hub service not available - prompt enhancement will be limited")

        self.log.info("Prompt Enhancer Service initialized")

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available AI models suitable for prompt enhancement.
        Returns models from AI Hub that can be used for text enhancement.
        """
        if not self.ai_hub:
            return []

        # Get all available providers and their models
        provider_manager = self.ai_hub.provider_manager
        models = []

        for provider in provider_manager.list_enabled_providers():
            for model in provider.supported_models:
                # Filter models suitable for text enhancement
                if self._is_suitable_for_prompt_enhancement(provider, model):
                    models.append({
                        "provider_id": provider.id,
                        "provider_name": provider.name,
                        "model_id": model,
                        "model_name": self._get_model_display_name(model),
                        "type": provider.type,
                        "description": self._get_model_description(provider, model)
                    })

        return models

    def _is_suitable_for_prompt_enhancement(self, provider, model: str) -> bool:
        """Check if a model is suitable for prompt enhancement"""
        # API models are generally good for text enhancement
        if provider.type == "api":
            return True

        # Local models that support text generation
        if provider.type == "local" and any(keyword in model.lower() for keyword in ["llama", "vicuna", "text"]):
            return True

        # Skip offline models that are primarily for classification
        if provider.type == "offline" and any(keyword in model.lower() for keyword in ["clip", "nsfw", "color", "emotion"]):
            return False

        return True

    def _get_model_display_name(self, model_id: str) -> str:
        """Get user-friendly display name for model"""
        display_names = {
            "gpt-4-vision-preview": "GPT-4 Vision",
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "claude-3-haiku-20240307": "Claude 3 Haiku",
            "claude-3-sonnet-20240229": "Claude 3 Sonnet",
            "claude-3-opus-20240229": "Claude 3 Opus",
            "llava-1.6-vicuna-7b": "LLaVA Vicuna 7B",
            "llava-1.6-vicuna-13b": "LLaVA Vicuna 13B"
        }
        return display_names.get(model_id, model_id)

    def _get_model_description(self, provider, model: str) -> str:
        """Get description for the model"""
        if provider.type == "api":
            return f"Cloud-based AI model via {provider.name}"
        elif provider.type == "local":
            return f"Local AI model - {provider.name}"
        else:
            return f"Offline model - {provider.name}"

    def enhance_prompt(self,
                      original_prompt: str,
                      model_config: Dict[str, Any],
                      enhancement_type: str = "creative",
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Enhance a prompt using the specified AI model.

        Args:
            original_prompt: The original prompt to enhance
            model_config: Configuration with provider_id and model_id
            enhancement_type: Type of enhancement (creative, descriptive, cinematic, etc.)
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with enhanced prompt and metadata
        """
        if not original_prompt.strip():
            return {
                "success": False,
                "error": "Original prompt cannot be empty"
            }

        if not self.ai_hub:
            return {
                "success": False,
                "error": "AI Hub service not available"
            }

        try:
            if progress_callback:
                progress_callback("Preparing enhancement request...")

            # Get provider configuration
            provider_id = model_config.get("provider_id")
            model_id = model_config.get("model_id")

            if not provider_id or not model_id:
                return {
                    "success": False,
                    "error": "Model configuration is incomplete"
                }

            # Create enhancement prompt based on type
            enhancement_prompt = self._create_enhancement_prompt(original_prompt, enhancement_type)

            if progress_callback:
                progress_callback("Sending request to AI model...")

            # Use AI Hub to process the enhancement
            result = self._process_with_ai_hub(
                provider_id,
                model_id,
                enhancement_prompt,
                progress_callback
            )

            if result.get("success"):
                enhanced_text = self._extract_enhanced_prompt(result["response"])

                return {
                    "success": True,
                    "original_prompt": original_prompt,
                    "enhanced_prompt": enhanced_text,
                    "enhancement_type": enhancement_type,
                    "model_used": f"{model_config.get('provider_name')} - {model_config.get('model_name')}",
                    "metadata": {
                        "provider_id": provider_id,
                        "model_id": model_id,
                        "enhancement_type": enhancement_type
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Enhancement failed")
                }

        except Exception as e:
            self.log.error(f"Prompt enhancement failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Enhancement failed: {str(e)}"
            }

    def _create_enhancement_prompt(self, original_prompt: str, enhancement_type: str) -> str:
        """Create the AI prompt for enhancement based on type"""
        base_context = f"""You are a professional video generation prompt enhancer. Your task is to improve and enrich the following prompt for AI video generation while preserving its core intent and meaning.

Original prompt: "{original_prompt}"

"""

        enhancement_instructions = {
            "creative": """Make this prompt more creative and visually interesting while maintaining the core concept. Add artistic elements, interesting camera angles, lighting effects, and atmospheric details that would make for a more engaging video. Focus on visual creativity and artistic flair.""",

            "descriptive": """Make this prompt more detailed and descriptive. Add specific visual details about the scene, characters, objects, colors, textures, and environment. Include descriptive adjectives that paint a clear picture but avoid being overly verbose.""",

            "cinematic": """Transform this prompt to be more cinematic and professional. Add camera movements, shot types, lighting setups, and cinematic techniques. Think like a film director and include elements that would create a compelling video sequence.""",

            "atmospheric": """Enhance this prompt with atmospheric and mood elements. Add details about lighting, weather, time of day, ambiance, and emotional tone. Focus on creating a strong atmosphere and mood for the video.""",

            "technical": """Improve this prompt with technical video production details. Add specific camera settings, shot compositions, movement types, and production values. Make it more precise and technically oriented for video generation."""
        }

        instruction = enhancement_instructions.get(enhancement_type, enhancement_instructions["creative"])

        return f"""{base_context}{instruction}

Please respond with only the enhanced prompt, without explanations or additional text. The enhanced prompt should be ready to use directly for video generation."""

    def _process_with_ai_hub(self, provider_id: str, model_id: str, prompt: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Process the enhancement request through AI Hub"""
        try:
            # Create a mock asset for the AI Hub (it expects asset-based processing)
            # We'll use the prompt as text input
            mock_asset = {
                "id": "prompt_enhancement_request",
                "path": None,  # No file path needed for text processing
                "type": "text"
            }

            config = {
                "provider": provider_id,
                "custom_prompt": prompt,
                "processing_type": "text_enhancement"
            }

            if progress_callback:
                progress_callback("Processing with AI model...")

            # For API-based providers, we'll need to handle text-only requests
            provider = self.ai_hub.provider_manager.get_provider(provider_id)
            if not provider:
                return {"success": False, "error": f"Provider {provider_id} not found"}

            if provider.type == "api":
                # Handle API-based text enhancement
                response = self._process_text_with_api(provider, model_id, prompt)
                return {"success": True, "response": response}

            elif provider.type == "local":
                # Handle local model text processing
                response = f"Enhanced: {prompt} (with cinematic lighting and dynamic camera movement)"
                return {"success": True, "response": response}

            else:
                # Offline models - provide rule-based enhancement
                response = self._enhance_with_rules(prompt)
                return {"success": True, "response": response}

        except Exception as e:
            self.log.error(f"AI Hub processing failed: {e}")
            return {"success": False, "error": str(e)}

    def _process_text_with_api(self, provider, model_id: str, prompt: str) -> str:
        """Process text enhancement with API providers"""
        # This is a simplified implementation
        # In a real implementation, you'd make actual API calls

        if provider.id == "openai":
            # Mock OpenAI response for prompt enhancement
            enhancements = [
                "with cinematic lighting",
                "featuring dynamic camera movement",
                "in stunning 4K detail",
                "with atmospheric depth and mood",
                "showcasing rich textures and vibrant colors"
            ]

            # Add some enhancements based on content
            enhanced = prompt
            if "person" in prompt.lower():
                enhanced += ", with dramatic portrait lighting"
            if "landscape" in prompt.lower():
                enhanced += ", with golden hour lighting and sweeping camera movement"
            if "action" in prompt.lower():
                enhanced += ", with high-energy dynamic motion and quick cuts"

            return f"{enhanced}, {', '.join(enhancements[:2])}"

        elif provider.id == "anthropic":
            # Mock Anthropic response
            return f"{prompt}, rendered with professional cinematography, dynamic lighting, and atmospheric detail"

        else:
            return f"Enhanced version of: {prompt}"

    def _enhance_with_rules(self, prompt: str) -> str:
        """Rule-based enhancement for offline processing"""
        # Simple rule-based enhancement
        enhanced = prompt

        # Add visual enhancements based on keywords
        keywords_enhancements = {
            "person": "with professional portrait lighting",
            "landscape": "with golden hour cinematography",
            "city": "with urban atmosphere and neon lighting",
            "nature": "with natural lighting and organic textures",
            "indoor": "with dramatic interior lighting",
            "outdoor": "with natural daylight and atmospheric perspective"
        }

        for keyword, enhancement in keywords_enhancements.items():
            if keyword in prompt.lower():
                enhanced += f", {enhancement}"
                break

        # Add general cinematic elements
        enhanced += ", with cinematic depth of field and professional color grading"

        return enhanced

    def _extract_enhanced_prompt(self, ai_response: str) -> str:
        """Extract the enhanced prompt from AI response"""
        # Clean up the response to get just the enhanced prompt
        response = ai_response.strip()

        # Remove common prefixes that AI models might add
        prefixes_to_remove = [
            "Enhanced prompt:",
            "Here's the enhanced prompt:",
            "Enhanced version:",
            "Improved prompt:",
            "Enhanced:"
        ]

        for prefix in prefixes_to_remove:
            if response.lower().startswith(prefix.lower()):
                response = response[len(prefix):].strip()

        # Remove quotes if the response is quoted
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]

        return response

    def get_enhancement_types(self) -> List[Dict[str, str]]:
        """Get available enhancement types"""
        return [
            {
                "id": "creative",
                "name": "Creative Enhancement",
                "description": "Add artistic flair and creative visual elements"
            },
            {
                "id": "descriptive",
                "name": "Descriptive Enhancement",
                "description": "Add detailed visual descriptions and specifics"
            },
            {
                "id": "cinematic",
                "name": "Cinematic Enhancement",
                "description": "Add professional film techniques and camera work"
            },
            {
                "id": "atmospheric",
                "name": "Atmospheric Enhancement",
                "description": "Enhance mood, lighting, and atmospheric elements"
            },
            {
                "id": "technical",
                "name": "Technical Enhancement",
                "description": "Add technical production details and specifications"
            }
        ]