# story_studio_project/plugins/core/plugin.py
from interfaces import IPlugin
from .services import SettingsService, DatabaseService
from .commands import PasteFromClipboardCommand, ReloadPluginsCommand

class Plugin(IPlugin):
    """
    This core plugin provides essential, non-UI services like project management
    and database access to the entire framework.
    """
    def register(self, framework):
        # 1. Create and register the settings service first, as it's a key dependency.
        settings_service = SettingsService(framework)
        framework.register_contribution(
            "services",
            {"id": "settings_service", "instance": settings_service}
        )

        # 2. Create the database service.
        db_service = DatabaseService(framework)

        # 3. Register the database service.
        # The obsolete call to initialize() is now removed. The service will
        # connect to the database automatically when it's first used.
        framework.register_contribution(
            "services",
            {"id": "database_service", "instance": db_service}
        )

        # 4. Register core commands
        framework.register_contribution(
            "commands",
            {"id": "assets.paste_from_clipboard", "class": PasteFromClipboardCommand}
        )

        framework.register_contribution(
            "commands",
            {"id": "framework.reload_plugins", "class": ReloadPluginsCommand}
        )
