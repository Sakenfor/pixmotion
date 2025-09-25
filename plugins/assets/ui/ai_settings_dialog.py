from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QPushButton, QGroupBox, QFormLayout, QTextEdit, QScrollArea,
    QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette


class AIProviderSettingsDialog(QDialog):
    """Dialog for configuring AI providers and tagging settings"""

    def __init__(self, framework, parent=None):
        super().__init__(parent)
        self.framework = framework
        self.provider_manager = None

        # Get AI provider manager
        ai_hub = framework.get_service("ai_hub")
        if ai_hub:
            self.provider_manager = ai_hub.provider_manager

        self.setWindowTitle("AI Tagging Settings")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("🤖 AI Tagging Configuration")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Provider tabs
        tabs.addTab(self._create_providers_tab(), "🔌 AI Providers")
        tabs.addTab(self._create_tagging_tab(), "🏷️ Tagging Settings")
        tabs.addTab(self._create_performance_tab(), "⚡ Performance")

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        test_btn = QPushButton("🧪 Test Connection")
        test_btn.clicked.connect(self._test_connection)
        button_layout.addWidget(test_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_providers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scroll area
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Provider configurations
        self.provider_widgets = {}

        if self.provider_manager:
            providers = self.provider_manager.list_providers()

            for provider in providers:
                group = self._create_provider_group(provider)
                scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        return widget

    def _create_provider_group(self, provider):
        """Create a group box for a single AI provider"""
        group = QGroupBox(f"{provider.name} ({provider.type.upper()})")
        layout = QFormLayout(group)

        # Store widgets for this provider
        self.provider_widgets[provider.id] = {}
        widgets = self.provider_widgets[provider.id]

        # Enabled checkbox
        widgets['enabled'] = QCheckBox("Enable this provider")
        widgets['enabled'].setChecked(provider.enabled)
        layout.addRow(widgets['enabled'])

        # Add separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addRow(line)

        # Provider-specific settings
        if provider.type == "api":
            widgets['api_key'] = QLineEdit()
            widgets['api_key'].setEchoMode(QLineEdit.EchoMode.Password)
            widgets['api_key'].setText(provider.settings.get("api_key", ""))
            widgets['api_key'].setPlaceholderText("Enter your API key")
            layout.addRow("🔑 API Key:", widgets['api_key'])

            widgets['model'] = QComboBox()
            widgets['model'].addItems(provider.supported_models)
            current_model = provider.settings.get("model", "")
            if current_model in provider.supported_models:
                widgets['model'].setCurrentText(current_model)
            layout.addRow("🧠 Model:", widgets['model'])

            widgets['max_tokens'] = QSpinBox()
            widgets['max_tokens'].setRange(50, 2000)
            widgets['max_tokens'].setValue(provider.settings.get("max_tokens", 300))
            layout.addRow("📝 Max Tokens:", widgets['max_tokens'])

            if "temperature" in provider.settings:
                widgets['temperature'] = QDoubleSpinBox()
                widgets['temperature'].setRange(0.0, 2.0)
                widgets['temperature'].setSingleStep(0.1)
                widgets['temperature'].setValue(provider.settings.get("temperature", 0.1))
                layout.addRow("🌡️ Temperature:", widgets['temperature'])

        elif provider.type == "local":
            widgets['model_path'] = QLineEdit()
            widgets['model_path'].setText(provider.settings.get("model_path", ""))
            widgets['model_path'].setPlaceholderText("Path to local model file")
            layout.addRow("📁 Model Path:", widgets['model_path'])

            widgets['gpu_enabled'] = QCheckBox("Use GPU acceleration")
            widgets['gpu_enabled'].setChecked(provider.settings.get("gpu_enabled", True))
            layout.addRow(widgets['gpu_enabled'])

            widgets['context_length'] = QSpinBox()
            widgets['context_length'].setRange(512, 8192)
            widgets['context_length'].setValue(provider.settings.get("context_length", 2048))
            layout.addRow("🧮 Context Length:", widgets['context_length'])

        elif provider.type == "offline":
            widgets['models_dir'] = QLineEdit()
            widgets['models_dir'].setText(provider.settings.get("models_dir", "models/"))
            widgets['models_dir'].setPlaceholderText("Directory containing offline models")
            layout.addRow("📂 Models Directory:", widgets['models_dir'])

            widgets['batch_size'] = QSpinBox()
            widgets['batch_size'].setRange(1, 128)
            widgets['batch_size'].setValue(provider.settings.get("batch_size", 32))
            layout.addRow("📦 Batch Size:", widgets['batch_size'])

        return group

    def _create_tagging_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Auto-tagging settings
        auto_group = QGroupBox("🚀 Automatic Tagging")
        auto_layout = QFormLayout(auto_group)

        self.auto_tag_new = QCheckBox("Auto-tag new assets")
        self.auto_tag_new.setChecked(True)
        self.auto_tag_new.setToolTip("Automatically run light AI tagging when new assets are added")
        auto_layout.addRow(self.auto_tag_new)

        self.auto_tag_priority = QComboBox()
        self.auto_tag_priority.addItems(["Light (Priority 1)", "Standard (Priority 2)", "Deep (Priority 3)"])
        self.auto_tag_priority.setToolTip("Priority level for automatic tagging")
        auto_layout.addRow("Default Priority:", self.auto_tag_priority)

        layout.addWidget(auto_group)

        # Tag layer settings
        layer_group = QGroupBox("🏷️ Tag Layer Configuration")
        layer_layout = QVBoxLayout(layer_group)

        info = QLabel("Tag layers define what AI analysis to perform on your assets.\n"
                     "• Light layers (Priority 1): Fast, for filtering\n"
                     "• Standard layers (Priority 2): Balanced quality/speed\n"
                     "• Deep layers (Priority 3): Detailed analysis for gameplay")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-style: italic;")
        layer_layout.addWidget(info)

        layer_info_btn = QPushButton("📋 View/Edit Tag Layers")
        layer_info_btn.clicked.connect(self._show_layer_editor)
        layer_layout.addWidget(layer_info_btn)

        layout.addWidget(layer_group)

        # Confidence settings
        conf_group = QGroupBox("🎯 Confidence & Quality")
        conf_layout = QFormLayout(conf_group)

        self.min_confidence = QDoubleSpinBox()
        self.min_confidence.setRange(0.0, 1.0)
        self.min_confidence.setSingleStep(0.1)
        self.min_confidence.setValue(0.3)
        self.min_confidence.setToolTip("Minimum confidence to accept AI tags")
        conf_layout.addRow("Min Confidence:", self.min_confidence)

        self.max_tags_per_layer = QSpinBox()
        self.max_tags_per_layer.setRange(1, 50)
        self.max_tags_per_layer.setValue(10)
        self.max_tags_per_layer.setToolTip("Maximum tags to keep per layer")
        conf_layout.addRow("Max Tags per Layer:", self.max_tags_per_layer)

        layout.addWidget(conf_group)
        layout.addStretch()

        return widget

    def _create_performance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Processing settings
        proc_group = QGroupBox("⚡ Processing Settings")
        proc_layout = QFormLayout(proc_group)

        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 100)
        self.batch_size.setValue(10)
        self.batch_size.setToolTip("Number of assets to process in each batch")
        proc_layout.addRow("Batch Size:", self.batch_size)

        self.concurrent_requests = QSpinBox()
        self.concurrent_requests.setRange(1, 10)
        self.concurrent_requests.setValue(3)
        self.concurrent_requests.setToolTip("Number of concurrent API requests")
        proc_layout.addRow("Concurrent Requests:", self.concurrent_requests)

        self.rate_limit_delay = QDoubleSpinBox()
        self.rate_limit_delay.setRange(0.0, 5.0)
        self.rate_limit_delay.setSingleStep(0.1)
        self.rate_limit_delay.setValue(0.1)
        self.rate_limit_delay.setSuffix(" seconds")
        self.rate_limit_delay.setToolTip("Delay between API requests to avoid rate limiting")
        proc_layout.addRow("Rate Limit Delay:", self.rate_limit_delay)

        layout.addWidget(proc_group)

        # Cache settings
        cache_group = QGroupBox("💾 Caching")
        cache_layout = QFormLayout(cache_group)

        self.enable_caching = QCheckBox("Enable result caching")
        self.enable_caching.setChecked(True)
        self.enable_caching.setToolTip("Cache AI analysis results to avoid reprocessing")
        cache_layout.addRow(self.enable_caching)

        self.cache_expire_days = QSpinBox()
        self.cache_expire_days.setRange(1, 365)
        self.cache_expire_days.setValue(30)
        self.cache_expire_days.setSuffix(" days")
        cache_layout.addRow("Cache Expiry:", self.cache_expire_days)

        layout.addWidget(cache_group)

        # Status info
        status_group = QGroupBox("📊 System Status")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self._update_status()
        status_layout.addWidget(self.status_text)

        refresh_btn = QPushButton("🔄 Refresh Status")
        refresh_btn.clicked.connect(self._update_status)
        status_layout.addWidget(refresh_btn)

        layout.addWidget(status_group)
        layout.addStretch()

        return widget

    def _load_settings(self):
        """Load current settings into the UI"""
        if not self.framework:
            return

        settings = self.framework.get_service("settings_service")
        if settings:
            # Load auto-tagging settings
            self.auto_tag_new.setChecked(settings.get("ai_auto_tag_new", True))
            priority = settings.get("ai_auto_tag_priority", 1)
            self.auto_tag_priority.setCurrentIndex(priority - 1)

            # Load performance settings
            self.batch_size.setValue(settings.get("ai_batch_size", 10))
            self.concurrent_requests.setValue(settings.get("ai_concurrent_requests", 3))
            self.rate_limit_delay.setValue(settings.get("ai_rate_limit_delay", 0.1))

            # Load quality settings
            self.min_confidence.setValue(settings.get("ai_min_confidence", 0.3))
            self.max_tags_per_layer.setValue(settings.get("ai_max_tags_per_layer", 10))

            # Load caching settings
            self.enable_caching.setChecked(settings.get("ai_enable_caching", True))
            self.cache_expire_days.setValue(settings.get("ai_cache_expire_days", 30))

    def _save_settings(self):
        """Save settings and close dialog"""
        if not self.framework:
            return

        settings = self.framework.get_service("settings_service")
        if not settings:
            return

        try:
            # Save provider settings
            if self.provider_manager:
                for provider_id, widgets in self.provider_widgets.items():
                    provider_settings = {
                        "enabled": widgets['enabled'].isChecked(),
                        "settings": {}
                    }

                    # Collect settings based on widget type
                    for key, widget in widgets.items():
                        if key == 'enabled':
                            continue
                        elif isinstance(widget, QLineEdit):
                            provider_settings["settings"][key] = widget.text()
                        elif isinstance(widget, QCheckBox):
                            provider_settings["settings"][key] = widget.isChecked()
                        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                            provider_settings["settings"][key] = widget.value()
                        elif isinstance(widget, QComboBox):
                            provider_settings["settings"][key] = widget.currentText()

                    self.provider_manager.update_provider(provider_id, provider_settings)

            # Save other settings
            settings.set("ai_auto_tag_new", self.auto_tag_new.isChecked())
            settings.set("ai_auto_tag_priority", self.auto_tag_priority.currentIndex() + 1)
            settings.set("ai_batch_size", self.batch_size.value())
            settings.set("ai_concurrent_requests", self.concurrent_requests.value())
            settings.set("ai_rate_limit_delay", self.rate_limit_delay.value())
            settings.set("ai_min_confidence", self.min_confidence.value())
            settings.set("ai_max_tags_per_layer", self.max_tags_per_layer.value())
            settings.set("ai_enable_caching", self.enable_caching.isChecked())
            settings.set("ai_cache_expire_days", self.cache_expire_days.value())

            self.accept()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")

    def _test_connection(self):
        """Test AI provider connections"""
        if not self.provider_manager:
            QMessageBox.information(self, "Test Connection", "AI provider manager not available")
            return

        enabled_providers = self.provider_manager.list_enabled_providers()
        if not enabled_providers:
            QMessageBox.warning(self, "Test Connection", "No AI providers are enabled")
            return

        # Test each enabled provider
        results = []
        for provider in enabled_providers:
            if provider.type == "offline":
                results.append(f"✅ {provider.name}: Available (offline)")
            elif provider.type == "api":
                api_key = provider.settings.get("api_key", "")
                if api_key:
                    results.append(f"🔑 {provider.name}: API key configured")
                else:
                    results.append(f"❌ {provider.name}: API key missing")
            elif provider.type == "local":
                model_path = provider.settings.get("model_path", "")
                if model_path:
                    results.append(f"💻 {provider.name}: Model path configured")
                else:
                    results.append(f"❌ {provider.name}: Model path missing")

        message = "Provider Status:\n\n" + "\n".join(results)
        QMessageBox.information(self, "Connection Test", message)

    def _show_layer_editor(self):
        """Open tag layer editor (placeholder)"""
        QMessageBox.information(self, "Tag Layer Editor",
                               "Tag layer editor will open the Tag Layer Editor panel.\n\n"
                               "You can edit layers there or use the Tag Layers dock panel.")

    def _update_status(self):
        """Update system status display"""
        status_lines = []

        if self.provider_manager:
            providers = self.provider_manager.list_providers()
            enabled_count = len([p for p in providers if p.enabled])
            status_lines.append(f"AI Providers: {enabled_count}/{len(providers)} enabled")

            for provider in providers:
                if provider.enabled:
                    status_lines.append(f"  ✅ {provider.name} ({provider.type})")
                else:
                    status_lines.append(f"  ⚪ {provider.name} (disabled)")

        # Add tag layer info
        tag_registry = self.framework.get_service("tag_layer_registry")
        if tag_registry:
            layers = tag_registry.list_layers()
            enabled_layers = [l for l in layers if l.get("enabled", True)]
            status_lines.append(f"\nTag Layers: {len(enabled_layers)}/{len(layers)} enabled")

        self.status_text.setPlainText("\n".join(status_lines))

