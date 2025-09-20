# story_studio_project/plugins/shell/plugin.py
from interfaces import IPlugin
from .main_window import MainWindow


class Plugin(IPlugin):
    """
    Registers the main application shell and the story editor panel
    by importing them from their dedicated modules.
    """

    def register(self, framework):
        # Register the main window shell
        framework.register_contribution(
            "shell",
            {"id": "main_shell", "class": MainWindow}
        )

        # Register the story editor as a central widget.
        # Note: In this architecture, the central widget is a special case
        # and not a standard dockable panel.
        #framework.register_contribution(
        #    "ui_central_widget",
        #    {"id": "story_editor", "class": StoryEditorPanel}
        #)

