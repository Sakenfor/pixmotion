"""
Test integration of the Prompt Enhancer Plugin

This test verifies that the plugin integrates properly with the existing codebase
without code duplication and follows established patterns.
"""
import sys
import os
from unittest.mock import Mock, MagicMock

# Add the project root to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

def test_plugin_structure():
    """Test that plugin follows the correct structure"""

    # Test plugin manifest exists and has required fields
    plugin_json_path = os.path.join(os.path.dirname(__file__), "plugin.json")
    assert os.path.exists(plugin_json_path), "plugin.json should exist"

    import json
    with open(plugin_json_path) as f:
        manifest = json.load(f)

    required_fields = ["uuid", "name", "version", "entry_point", "dependencies"]
    for field in required_fields:
        assert field in manifest, f"Manifest should contain {field}"

    # Test that dependencies include the required plugins
    assert "Core Services" in manifest["dependencies"]
    assert "Asset Library" in manifest["dependencies"]
    assert "Pixverse Generation" in manifest["dependencies"]

    print("[PASS] Plugin structure test passed")


def test_service_registration():
    """Test that the service can be registered properly"""

    from plugins.prompt_enhancer.services import PromptEnhancerService

    # Mock framework
    framework = Mock()
    log_manager = Mock()
    framework.get_service.return_value = log_manager

    # Create service
    service = PromptEnhancerService(framework)
    assert service.framework == framework

    # Test initialization
    service.initialize()

    print("[PASS] Service registration test passed")


def test_ai_hub_integration():
    """Test integration with AI Hub service"""

    from plugins.prompt_enhancer.services import PromptEnhancerService

    # Mock framework and AI Hub
    framework = Mock()
    ai_hub = Mock()
    settings = Mock()
    log_manager = Mock()

    # Setup provider manager mock
    provider_manager = Mock()
    ai_hub.provider_manager = provider_manager

    # Mock provider
    mock_provider = Mock()
    mock_provider.id = "test_provider"
    mock_provider.name = "Test Provider"
    mock_provider.type = "api"
    mock_provider.enabled = True
    mock_provider.supported_models = ["test-model"]

    provider_manager.list_enabled_providers.return_value = [mock_provider]

    framework.get_service.side_effect = lambda name: {
        "ai_hub": ai_hub,
        "settings_service": settings,
        "log_manager": log_manager
    }.get(name)

    # Create service
    service = PromptEnhancerService(framework)
    service.initialize()

    # Test getting available models
    models = service.get_available_models()
    assert len(models) > 0
    assert models[0]["provider_id"] == "test_provider"
    assert models[0]["model_id"] == "test-model"

    print("[PASS] AI Hub integration test passed")


def test_no_code_duplication():
    """Test that we don't duplicate existing functionality"""

    # Import our modules
    from plugins.prompt_enhancer import services, widgets, extension

    # Check that we're using existing interfaces, not duplicating them
    from plugins.prompt_enhancer.services import PromptEnhancerService
    from interfaces import IService

    assert issubclass(PromptEnhancerService, IService), "Should extend IService interface"

    # Verify we're not duplicating AI Hub functionality
    service_code = open(os.path.join(os.path.dirname(__file__), "services.py")).read()

    # Should not contain duplicated AI provider logic
    assert "class AIProviderManager" not in service_code, "Should not duplicate AIProviderManager"
    assert "class AIHubService" not in service_code, "Should not duplicate AIHubService"

    # Should use existing AI Hub service
    assert "self.ai_hub = self.framework.get_service" in service_code, "Should use existing AI Hub service"

    print("[PASS] No code duplication test passed")


def test_ui_extension_pattern():
    """Test that UI extension follows proper patterns"""

    from plugins.prompt_enhancer.extension import GeneratorPanelExtension

    # Mock framework
    framework = Mock()
    events = Mock()
    log_manager = Mock()

    framework.get_service.side_effect = lambda name: {
        "event_manager": events,
        "log_manager": log_manager
    }.get(name)

    # Create extension
    extension = GeneratorPanelExtension(framework)

    # Verify it subscribes to the correct event
    events.subscribe.assert_called_with("generator_panel_initialized", extension._on_panel_initialized)

    print("[PASS] UI extension pattern test passed")


def test_enhancement_types():
    """Test that enhancement types are properly defined"""

    from plugins.prompt_enhancer.services import PromptEnhancerService

    framework = Mock()
    framework.get_service.return_value = Mock()

    service = PromptEnhancerService(framework)
    types = service.get_enhancement_types()

    assert len(types) > 0, "Should have enhancement types"

    required_fields = ["id", "name", "description"]
    for enhancement_type in types:
        for field in required_fields:
            assert field in enhancement_type, f"Enhancement type should have {field}"

    # Check for expected enhancement types
    type_ids = [t["id"] for t in types]
    expected_types = ["creative", "descriptive", "cinematic", "atmospheric", "technical"]
    for expected in expected_types:
        assert expected in type_ids, f"Should have {expected} enhancement type"

    print("[PASS] Enhancement types test passed")


def run_all_tests():
    """Run all integration tests"""
    print("Running Prompt Enhancer Plugin Integration Tests...")
    print("=" * 50)

    try:
        test_plugin_structure()
        test_service_registration()
        test_ai_hub_integration()
        test_no_code_duplication()
        test_ui_extension_pattern()
        test_enhancement_types()

        print("=" * 50)
        print("[SUCCESS] All tests passed! Plugin integration successful.")
        return True

    except Exception as e:
        print(f"[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)