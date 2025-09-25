"""
Generator Panel Extension for Prompt Enhancement

This module extends the existing Generator Panel to add prompt enhancement functionality
without duplicating code or creating a separate panel.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSplitter, QTabWidget
from PyQt6.QtCore import QTimer, Qt
from .widgets import PromptEnhancementWidget


class GeneratorPanelExtension:
    """
    Extension that integrates prompt enhancement functionality into the existing Generator Panel.
    This follows the extension pattern to avoid code duplication.
    """

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.events = framework.get_service("event_manager")
        self.enhancement_widget = None
        self.target_panel = None
        self.initialized = False

        # Use event system to hook into panel initialization
        self.events.subscribe("generator_panel_initialized", self._on_panel_initialized)

    def _on_panel_initialized(self, **kwargs):
        """Handle generator panel initialization"""
        panel_instance = kwargs.get('panel')
        if not panel_instance:
            return

        self.target_panel = panel_instance
        self.log.info("Generator panel initialized, adding prompt enhancement")

        # Use a small delay to ensure the panel is fully constructed
        QTimer.singleShot(100, self._extend_generator_panel)

    def _extend_generator_panel(self):
        """Add prompt enhancement as a tab in the existing Generator Panel"""
        if self.initialized:
            return  # Already initialized

        try:
            # Find the tab widget in the generator panel
            tab_widget = None
            for child in self.target_panel.findChildren(QTabWidget):
                tab_widget = child
                break

            if not tab_widget:
                self.log.error("Could not find tab widget in generator panel")
                return

            # Create the enhancement widget for the tab
            self.enhancement_widget = PromptEnhancementWidget(self.framework)

            # Add the prompt enhancer as a new tab
            tab_widget.addTab(self.enhancement_widget, "✨ Enhance")

            # Initialize the service
            self.enhancement_widget.initialize_service()

            self.log.info("Successfully added Prompt Enhancer tab to Generator Panel")
            self.initialized = True

            # Connect enhancement signal to update the prompt
            self.enhancement_widget.prompt_enhanced.connect(self._on_prompt_enhanced)

        except Exception as e:
            self.log.error(f"Failed to extend generator panel: {e}", exc_info=True)

    def _on_prompt_enhanced(self, enhanced_prompt: str):
        """Handle prompt enhancement completion"""
        self.log.info("Prompt enhancement completed and applied to generator panel")

        # Publish event for other plugins that might be interested
        self.events.publish("prompt_enhanced", {
            "enhanced_prompt": enhanced_prompt,
            "source": "prompt_enhancer_plugin"
        })

    def integrate_with_existing_panel(self, generator_panel):
        """
        Alternative method to integrate with the generator panel directly.
        This can be called by the generator panel if it supports extensions.
        """
        self.target_panel = generator_panel
        self._extend_generator_panel()