"""
Prompt Enhancement UI Widgets
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QProgressBar, QTextEdit, QFrame, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import Dict, Any, Optional, Callable


class PromptEnhancementWorker(QThread):
    """Worker thread for prompt enhancement to avoid blocking UI"""

    finished = pyqtSignal(dict)  # Emits the enhancement result
    progress = pyqtSignal(str)   # Emits progress messages
    error = pyqtSignal(str)      # Emits error messages

    def __init__(self, enhancer_service, original_prompt: str, model_config: Dict[str, Any], enhancement_type: str):
        super().__init__()
        self.enhancer_service = enhancer_service
        self.original_prompt = original_prompt
        self.model_config = model_config
        self.enhancement_type = enhancement_type

    def run(self):
        """Run the enhancement in the background"""
        try:
            def progress_callback(message: str):
                self.progress.emit(message)

            result = self.enhancer_service.enhance_prompt(
                self.original_prompt,
                self.model_config,
                self.enhancement_type,
                progress_callback
            )

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class PromptEnhancementWidget(QFrame):
    """
    Widget that provides prompt enhancement functionality.
    Designed to be integrated into the existing Generator Panel.
    """

    prompt_enhanced = pyqtSignal(str)  # Emits enhanced prompt when ready

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.enhancer_service = None
        self.enhancement_worker = None

        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header_layout = QHBoxLayout()

        header_label = QLabel("✨ Prompt Enhancement")
        font = QFont()
        font.setBold(True)
        header_label.setFont(font)
        header_layout.addWidget(header_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        model_layout.addWidget(self.model_combo)

        model_layout.addStretch()
        layout.addLayout(model_layout)

        # Enhancement type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Style:"))

        self.enhancement_type_combo = QComboBox()
        self.enhancement_type_combo.setMinimumWidth(150)
        type_layout.addWidget(self.enhancement_type_combo)

        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Action buttons
        button_layout = QHBoxLayout()

        self.enhance_btn = QPushButton("✨ Enhance Prompt")
        self.enhance_btn.setMinimumHeight(32)
        button_layout.addWidget(self.enhance_btn)

        self.preview_btn = QPushButton("👁 Preview")
        self.preview_btn.setMinimumHeight(32)
        button_layout.addWidget(self.preview_btn)

        layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Initially disabled until service is available
        self.setEnabled(False)

    def _connect_signals(self):
        """Connect UI signals"""
        self.enhance_btn.clicked.connect(self._on_enhance_clicked)
        self.preview_btn.clicked.connect(self._on_preview_clicked)

    def initialize_service(self):
        """Initialize the enhancer service - called after plugin loading"""
        try:
            self.enhancer_service = self.framework.get_service("prompt_enhancer_service")
            if self.enhancer_service:
                self._populate_models()
                self._populate_enhancement_types()
                self.setEnabled(True)
                self.status_label.setText("Ready for prompt enhancement")
                self.status_label.setVisible(True)
                self.log.info("Prompt enhancement widget initialized successfully")
            else:
                self.log.warning("Prompt enhancer service not available")
                self.status_label.setText("Enhancement service unavailable")
                self.status_label.setVisible(True)
        except Exception as e:
            self.log.error(f"Failed to initialize prompt enhancement widget: {e}")
            self.status_label.setText("Enhancement service error")
            self.status_label.setVisible(True)

    def _populate_models(self):
        """Populate the model selection combo box"""
        if not self.enhancer_service:
            return

        models = self.enhancer_service.get_available_models()
        self.model_combo.clear()

        if not models:
            self.model_combo.addItem("No models available", None)
            self.enhance_btn.setEnabled(False)
            return

        for model in models:
            display_text = f"{model['model_name']} ({model['provider_name']})"
            self.model_combo.addItem(display_text, model)

        self.enhance_btn.setEnabled(True)

    def _populate_enhancement_types(self):
        """Populate the enhancement type combo box"""
        if not self.enhancer_service:
            return

        types = self.enhancer_service.get_enhancement_types()
        self.enhancement_type_combo.clear()

        for enhancement_type in types:
            self.enhancement_type_combo.addItem(
                enhancement_type['name'],
                enhancement_type['id']
            )

    def _on_enhance_clicked(self):
        """Handle enhance button click"""
        if not self.enhancer_service:
            QMessageBox.warning(self, "Error", "Enhancement service not available")
            return

        # Get the current prompt from the parent widget
        prompt_text = self._get_current_prompt()
        if not prompt_text.strip():
            QMessageBox.warning(self, "Error", "Please enter a prompt to enhance")
            return

        model_config = self.model_combo.currentData()
        if not model_config:
            QMessageBox.warning(self, "Error", "Please select a model")
            return

        enhancement_type = self.enhancement_type_combo.currentData()
        if not enhancement_type:
            enhancement_type = "creative"

        self._start_enhancement(prompt_text, model_config, enhancement_type)

    def _on_preview_clicked(self):
        """Handle preview button click"""
        # For now, preview shows a dialog with the current prompt
        # In the future, this could show a preview of potential enhancements
        current_prompt = self._get_current_prompt()
        if current_prompt.strip():
            QMessageBox.information(
                self,
                "Current Prompt Preview",
                f"Current prompt:\n\n{current_prompt}"
            )
        else:
            QMessageBox.warning(self, "No Prompt", "Please enter a prompt first")

    def _get_current_prompt(self) -> str:
        """Get the current prompt from the Generator Panel"""
        # Find the parent Generator Panel and get the prompt text
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'prompt_edit'):
                return parent_widget.prompt_edit.toPlainText()
            parent_widget = parent_widget.parent()
        return ""

    def _set_current_prompt(self, prompt: str):
        """Set the prompt in the Generator Panel"""
        # Find the parent Generator Panel and set the prompt text
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'prompt_edit'):
                parent_widget.prompt_edit.setPlainText(prompt)
                return
            parent_widget = parent_widget.parent()

    def _start_enhancement(self, original_prompt: str, model_config: Dict[str, Any], enhancement_type: str):
        """Start the enhancement process in a background thread"""
        if self.enhancement_worker and self.enhancement_worker.isRunning():
            QMessageBox.information(self, "In Progress", "Enhancement already in progress. Please wait.")
            return

        # Update UI for processing state
        self.enhance_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        self.status_label.setText("Enhancing prompt...")
        self.status_label.setVisible(True)

        # Create and start worker thread
        self.enhancement_worker = PromptEnhancementWorker(
            self.enhancer_service,
            original_prompt,
            model_config,
            enhancement_type
        )

        self.enhancement_worker.finished.connect(self._on_enhancement_finished)
        self.enhancement_worker.progress.connect(self._on_enhancement_progress)
        self.enhancement_worker.error.connect(self._on_enhancement_error)

        self.enhancement_worker.start()

    def _on_enhancement_progress(self, message: str):
        """Handle progress updates from enhancement worker"""
        self.status_label.setText(message)

    def _on_enhancement_finished(self, result: Dict[str, Any]):
        """Handle enhancement completion"""
        # Reset UI state
        self.enhance_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if result.get("success"):
            enhanced_prompt = result.get("enhanced_prompt", "")
            self.status_label.setText(f"Enhanced using {result.get('model_used', 'AI model')}")

            # Show confirmation dialog before applying
            response = QMessageBox.question(
                self,
                "Enhancement Complete",
                f"Original prompt:\n{result.get('original_prompt', '')}\n\n"
                f"Enhanced prompt:\n{enhanced_prompt}\n\n"
                f"Apply enhanced prompt?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if response == QMessageBox.StandardButton.Yes:
                self._set_current_prompt(enhanced_prompt)
                self.prompt_enhanced.emit(enhanced_prompt)
                self.log.info("Prompt enhancement applied successfully")

        else:
            error_message = result.get("error", "Unknown error")
            self.status_label.setText(f"Enhancement failed: {error_message}")
            QMessageBox.warning(self, "Enhancement Failed", f"Failed to enhance prompt:\n{error_message}")

        # Clean up worker
        if self.enhancement_worker:
            self.enhancement_worker.deleteLater()
            self.enhancement_worker = None

    def _on_enhancement_error(self, error_message: str):
        """Handle enhancement errors"""
        # Reset UI state
        self.enhance_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_message}")

        QMessageBox.critical(self, "Enhancement Error", f"Enhancement failed with error:\n{error_message}")

        # Clean up worker
        if self.enhancement_worker:
            self.enhancement_worker.deleteLater()
            self.enhancement_worker = None


class CompactPromptEnhancer(QWidget):
    """
    Compact version of prompt enhancer for integration into existing UI.
    Shows just the essential controls.
    """

    prompt_enhanced = pyqtSignal(str)

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.enhancer_widget = PromptEnhancementWidget(framework, self)
        self._setup_ui()

    def _setup_ui(self):
        """Setup compact UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.enhancer_widget)

        # Connect signals
        self.enhancer_widget.prompt_enhanced.connect(self.prompt_enhanced)

    def initialize_service(self):
        """Initialize the enhancer service"""
        self.enhancer_widget.initialize_service()