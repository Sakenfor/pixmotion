"""Tests for the Framework class and core services."""

import unittest
from unittest.mock import Mock, patch

from framework import Framework


class TestFramework(unittest.TestCase):
    """Test cases for the Framework class."""

    def setUp(self):
        """Set up test environment."""
        self.framework = Framework()

    def test_framework_initialization(self):
        """Test that framework initializes with all core services."""
        # Check that core services are registered
        self.assertIsNotNone(self.framework.get_service("log_manager"))
        self.assertIsNotNone(self.framework.get_service("event_manager"))
        self.assertIsNotNone(self.framework.get_service("service_manager"))
        self.assertIsNotNone(self.framework.get_service("worker_manager"))
        self.assertIsNotNone(self.framework.get_service("history_manager"))

    def test_service_retrieval(self):
        """Test that services can be retrieved by name."""
        log_service = self.framework.get_service("log_manager")
        self.assertIsNotNone(log_service)
        self.assertTrue(hasattr(log_service, "info"))
        self.assertTrue(hasattr(log_service, "error"))

    def test_contribution_registration(self):
        """Test that contributions can be registered and retrieved."""
        test_contribution = {"id": "test", "value": "test_value"}
        self.framework.register_contribution("test_point", test_contribution)

        contributions = self.framework.get_contributions("test_point")
        self.assertEqual(len(contributions), 1)
        self.assertEqual(contributions[0]["value"], "test_value")

    def test_plugin_context(self):
        """Test plugin context management."""
        # Initially no active plugin
        self.assertIsNone(self.framework.get_active_plugin_uuid())

        # Push a plugin context
        self.framework._push_plugin_context("test-plugin-uuid")
        self.assertEqual(self.framework.get_active_plugin_uuid(), "test-plugin-uuid")

        # Push another
        self.framework._push_plugin_context("another-plugin-uuid")
        self.assertEqual(self.framework.get_active_plugin_uuid(), "another-plugin-uuid")

        # Pop back
        self.framework._pop_plugin_context()
        self.assertEqual(self.framework.get_active_plugin_uuid(), "test-plugin-uuid")

        # Pop final
        self.framework._pop_plugin_context()
        self.assertIsNone(self.framework.get_active_plugin_uuid())


class TestEventManager(unittest.TestCase):
    """Test cases for the EventManager service."""

    def setUp(self):
        """Set up test environment."""
        self.framework = Framework()
        self.event_manager = self.framework.get_service("event_manager")

    def test_event_subscription_and_publishing(self):
        """Test that events can be subscribed to and published."""
        callback_called = False
        callback_data = None

        def test_callback(**kwargs):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = kwargs

        # Subscribe to event
        self.event_manager.subscribe("test_event", test_callback)

        # Publish event
        self.event_manager.publish("test_event", data="test_data", value=42)

        # Check callback was called with correct data
        self.assertTrue(callback_called)
        self.assertEqual(callback_data["data"], "test_data")
        self.assertEqual(callback_data["value"], 42)

    def test_publish_chain(self):
        """Test cancellable event chains."""
        call_order = []

        def callback1(data_object):
            call_order.append("callback1")
            data_object["processed_by"] = ["callback1"]

        def callback2(data_object):
            call_order.append("callback2")
            data_object["processed_by"].append("callback2")
            # Cancel the chain
            data_object["is_cancelled"] = True

        def callback3(data_object):
            call_order.append("callback3")  # This should not be called
            data_object["processed_by"].append("callback3")

        # Subscribe callbacks
        self.event_manager.subscribe("chain_event", callback1)
        self.event_manager.subscribe("chain_event", callback2)
        self.event_manager.subscribe("chain_event", callback3)

        # Publish chain event
        data_object = {"processed_by": []}
        result = self.event_manager.publish_chain("chain_event", data_object)

        # Check that chain was cancelled and callback3 wasn't called
        self.assertTrue(result["is_cancelled"])
        self.assertEqual(call_order, ["callback1", "callback2"])
        self.assertEqual(result["processed_by"], ["callback1", "callback2"])


class TestCommandManager(unittest.TestCase):
    """Test cases for the CommandManager service."""

    def setUp(self):
        """Set up test environment."""
        self.framework = Framework()
        self.command_manager = self.framework.get_service("command_manager")

    def test_command_registration_and_execution(self):
        """Test command registration and execution."""
        # Create a mock command class
        class TestCommand:
            def __init__(self, framework):
                self.framework = framework
                self.executed = False
                self.kwargs_received = None

            def execute(self, **kwargs):
                self.executed = True
                self.kwargs_received = kwargs
                return "test_result"

        # Register the command
        self.command_manager.register("test_command", TestCommand)

        # Execute the command
        result = self.command_manager.execute("test_command", arg1="value1", arg2=42)

        # Check execution
        self.assertEqual(result, "test_result")


if __name__ == '__main__':
    unittest.main()