# D:/My Drive/code/pixmotion/plugins/core/services.py
import os
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from framework.config_manager import ConfigManager


class SettingsService:
    """Manages application settings using proper OS conventions."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.config_manager = ConfigManager()

        # Migrate old settings if they exist
        old_settings_path = Path(framework.get_project_root()) / "app_settings.json"
        if old_settings_path.exists():
            self.config_manager.migrate_old_settings(old_settings_path)
            self.log.info("Migrated settings to user directories")

        self.settings = self.config_manager.load_settings()
        self._user_data_root_path = Path(self.config_manager.user_data_dir)

    def get(self, key, default=None):
        return self.config_manager.get(key, default)

    def set(self, key, value):
        self.config_manager.set(key, value)
        if key == "user_data_root":
            self._user_data_root_path = Path(self.config_manager.user_data_dir)

    def resolve_user_path(self, *parts: str, ensure_exists: bool = True) -> str:
        """Resolve a path relative to the configured user data root."""

        cleaned_parts: list[str] = []
        for part in parts:
            if part is None:
                continue
            text = str(part).strip()
            if not text:
                continue
            cleaned_parts.append(text.replace("\\", os.sep))

        path: Path | None = None
        for raw in cleaned_parts:
            candidate = Path(raw).expanduser()
            if candidate.is_absolute():
                path = candidate
            else:
                if path is None:
                    path = self._user_data_root_path / candidate
                else:
                    path = path / candidate

        if path is None:
            path = self._user_data_root_path

        path = Path(os.path.normpath(str(path)))

        if ensure_exists:
            last_name = Path(cleaned_parts[-1]).name if cleaned_parts else ""
            is_probably_file = bool(last_name) and "." in last_name and not last_name.startswith(".")
            target_dir = path.parent if is_probably_file else path
            target_dir.mkdir(parents=True, exist_ok=True)

        return str(path)

    def get_pixverse_api_key(self):
        """Get Pixverse API key from environment or config."""
        return self.config_manager.get_pixverse_api_key()


class DatabaseService:
    """Manages database connections and sessions."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        settings = framework.get_service("settings_service")

        # Use the config manager's database path
        db_path = settings.config_manager.database_path
        db_uri = f"sqlite:///{db_path}"
        self.log.info(f"Database URI set to: {db_uri}")

        self.engine = create_engine(db_uri)
        self.Session = sessionmaker(bind=self.engine)

    def create_all_tables(self):
        """
        Creates all discovered tables.
        This is called by the framework *after* all plugins have loaded and
        had a chance to contribute their models by importing them.
        """
        self.log.info("Creating all registered database tables...")
        # Because all plugin models inherit from the core's shared Base,
        # this single call will discover and create tables for all plugins.
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.Session()

    def query(self, model, filter_func=None):
        session = self.get_session()
        try:
            query = session.query(model)
            if filter_func:
                query = query.filter(filter_func(model))
            return query.all()
        finally:
            session.close()
