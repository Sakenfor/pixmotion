# D:/My Drive/code/pixmotion/plugins/core/services.py
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base


class SettingsService:
    """Manages application settings from a JSON file."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self.settings_path = os.path.join(framework.get_project_root(), "app_settings.json")
        self.settings = self._load_settings()

    def _load_settings(self):
        try:
            with open(self.settings_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.log.warning("Settings file not found or invalid. Using defaults.")
            return {}

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self._save_settings()

    def _save_settings(self):
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            self.log.error(f"Failed to save settings: {e}")


class DatabaseService:
    """Manages database connections and sessions."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        settings = framework.get_service("settings_service")

        project_root = self.framework.get_project_root()
        data_dir = os.path.join(project_root, "data")
        os.makedirs(data_dir, exist_ok=True)

        db_filename = settings.get("database_filename", "pixmotion.db")
        db_path = os.path.join(data_dir, db_filename)
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
