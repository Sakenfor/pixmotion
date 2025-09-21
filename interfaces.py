# story_studio_project/interfaces.py
class IPlugin:
    """
    The main interface for a plugin. The 'plugin.py' file in each plugin's
    folder must contain a class that implements this interface.
    """

    def register(self, framework):
        """Called by the plugin manager to register all contributions."""
        raise NotImplementedError


class ICommand:
    """Interface for an executable command."""

    def __init__(self, framework):
        self.framework = framework

    def execute(self, **kwargs):
        """The main execution method for the command."""
        raise NotImplementedError


class IUndoableCommand(ICommand):
    """
    Interface for a command that supports undo/redo functionality.
    The command_manager will automatically add these to the history_manager.
    """

    def undo(self):
        """Reverts the action performed by execute()."""
        raise NotImplementedError

    def redo(self):
        """Re-applies the action performed by execute()."""
        raise NotImplementedError
