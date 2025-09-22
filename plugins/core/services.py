# D:/My Drive/code/pixmotion/plugins/core/services.py
import os
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


class SettingsService:
    """Manages application settings from a JSON file."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        self._project_root = Path(framework.get_project_root())
        self.settings_path = os.path.join(
            framework.get_project_root(), "app_settings.json"
        )
        self.settings = self._load_settings()
        if "user_data_root" not in self.settings:
            self.settings["user_data_root"] = "data"
        self._user_data_root_path = self._compute_user_data_root_path()

    def _load_settings(self):
        try:
            with open(self.settings_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.log.warning("Settings file not found or invalid. Using defaults.")
            return {}

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        if key == "user_data_root":
            self._user_data_root_path = self._compute_user_data_root_path(value)
        self._save_settings()

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

    def _compute_user_data_root_path(self, value: str | None = None) -> Path:
        root_value = str(value if value is not None else self.settings.get("user_data_root", "data") or "data")
        candidate = Path(root_value.replace("\\", os.sep)).expanduser()
        if not candidate.is_absolute():
            candidate = self._project_root / candidate
        candidate = Path(os.path.normpath(str(candidate)))
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    def _save_settings(self):
        try:
            with open(self.settings_path, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            self.log.error(f"Failed to save settings: {e}")


class DatabaseService:
    """Manages database connections and sessions."""

    def __init__(self, framework):
        self.framework = framework
        self.log = framework.get_service("log_manager")
        settings = framework.get_service("settings_service")

        db_filename = settings.get("database_filename", "pixmotion.db")
        if os.path.isabs(db_filename):
            db_path = db_filename
            os.makedirs(os.path.dirname(db_path) or os.curdir, exist_ok=True)
        else:
            db_path = settings.resolve_user_path(db_filename)
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
