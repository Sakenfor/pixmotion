# story_studio_project/interfaces.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IPlugin(ABC):
    """
    The main interface for a plugin. The 'plugin.py' file in each plugin's
    folder must contain a class that implements this interface.
    """

    @abstractmethod
    def register(self, framework):
        """Called by the plugin manager to register all contributions."""
        pass


class ICommand(ABC):
    """Interface for an executable command."""

    def __init__(self, framework):
        self.framework = framework

    @abstractmethod
    def execute(self, **kwargs):
        """The main execution method for the command."""
        pass


class IUndoableCommand(ICommand):
    """
    Interface for a command that supports undo/redo functionality.
    The command_manager will automatically add these to the history_manager.
    """

    @abstractmethod
    def undo(self):
        """Reverts the action performed by execute()."""
        pass

    @abstractmethod
    def redo(self):
        """Re-applies the action performed by execute()."""
        pass


class IService(ABC):
    """Base interface for all services."""

    def __init__(self, framework):
        self.framework = framework

    def initialize(self):
        """Initialize the service. Called after all services are registered."""
        pass

    def shutdown(self):
        """Cleanup resources. Called during application shutdown."""
        pass


class ISettingsService(IService):
    """Interface for settings management service."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any):
        """Set a setting value."""
        pass

    @abstractmethod
    def resolve_user_path(self, *parts: str, ensure_exists: bool = True) -> str:
        """Resolve a path relative to user data directory."""
        pass


class IDatabaseService(IService):
    """Interface for database service."""

    @abstractmethod
    def get_session(self):
        """Get a database session."""
        pass

    @abstractmethod
    def create_all_tables(self):
        """Create all registered database tables."""
        pass

    @abstractmethod
    def query(self, model, filter_func=None):
        """Query the database."""
        pass


class IAssetService(IService):
    """Interface for asset management service."""

    @abstractmethod
    def add_asset(self, file_path: str):
        """Add an asset to the database."""
        pass

    @abstractmethod
    def get_asset_path(self, asset_id: str) -> Optional[str]:
        """Get the file path for an asset."""
        pass

    @abstractmethod
    def scan_folder(self, folder_path: str) -> int:
        """Scan a folder for assets and add them to the database."""
        pass


class IEventManager(IService):
    """Interface for event management service."""

    @abstractmethod
    def subscribe(self, event_name: str, callback):
        """Subscribe to an event."""
        pass

    @abstractmethod
    def publish(self, event_name: str, **kwargs):
        """Publish an event."""
        pass

    @abstractmethod
    def publish_chain(self, event_name: str, data_object: Dict[str, Any]):
        """Publish a cancellable event chain."""
        pass


class ILogManager(IService):
    """Interface for logging service."""

    @abstractmethod
    def info(self, msg: str, *args, **kwargs):
        """Log an info message."""
        pass

    @abstractmethod
    def warning(self, msg: str, *args, **kwargs):
        """Log a warning message."""
        pass

    @abstractmethod
    def error(self, msg: str, *args, **kwargs):
        """Log an error message."""
        pass

    @abstractmethod
    def debug(self, msg: str):
        """Log a debug message."""
        pass

    @abstractmethod
    def notification(self, message: str):
        """Send a user notification."""
        pass
