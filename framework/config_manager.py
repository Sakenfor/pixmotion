"""
Configuration Manager for PixMotion
Handles cross-platform user directory management and settings storage.
"""
import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration and user directories following OS conventions."""

    def __init__(self):
        self.app_name = "PixMotion"
        self._config_cache = {}
        self._setup_directories()

    def _setup_directories(self):
        """Setup platform-specific directories for config, data, and cache."""
        system = platform.system().lower()

        if system == "windows":
            # Windows paths
            self.config_dir = Path(os.environ.get("APPDATA", "")) / self.app_name
            self.user_data_dir = Path(os.environ.get("USERPROFILE", "")) / "Documents" / self.app_name
            self.cache_dir = Path(os.environ.get("LOCALAPPDATA", "")) / self.app_name

        elif system == "darwin":  # macOS
            home = Path.home()
            self.config_dir = home / "Library" / "Application Support" / self.app_name
            self.user_data_dir = home / "Documents" / self.app_name
            self.cache_dir = home / "Library" / "Caches" / self.app_name

        else:  # Linux/Unix
            home = Path.home()
            self.config_dir = home / ".config" / self.app_name
            self.user_data_dir = home / "Documents" / self.app_name
            self.cache_dir = home / ".cache" / self.app_name

        # Create directories if they don't exist
        for directory in [self.config_dir, self.user_data_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def settings_file(self) -> Path:
        """Path to the main settings file."""
        return self.config_dir / "settings.json"

    @property
    def database_path(self) -> Path:
        """Path to the database file."""
        return self.user_data_dir / "pixmotion.db"

    @property
    def thumbnails_dir(self) -> Path:
        """Directory for thumbnail cache."""
        thumbnails = self.cache_dir / "thumbnails"
        thumbnails.mkdir(exist_ok=True)
        return thumbnails

    @property
    def ai_models_dir(self) -> Path:
        """Directory for AI models."""
        models = self.user_data_dir / "ai_models"
        models.mkdir(exist_ok=True)
        return models

    @property
    def output_dir(self) -> Path:
        """Default output directory for generated content."""
        output = self.user_data_dir / "output"
        output.mkdir(exist_ok=True)
        return output

    def get_default_library_folders(self) -> list:
        """Get platform-appropriate default library folders."""
        system = platform.system().lower()
        folders = []

        if system == "windows":
            # Common Windows media folders
            user_profile = Path(os.environ.get("USERPROFILE", ""))
            folders.extend([
                str(user_profile / "Pictures"),
                str(user_profile / "Videos"),
                str(self.user_data_dir / "assets")
            ])
        elif system == "darwin":  # macOS
            home = Path.home()
            folders.extend([
                str(home / "Pictures"),
                str(home / "Movies"),
                str(self.user_data_dir / "assets")
            ])
        else:  # Linux
            home = Path.home()
            folders.extend([
                str(home / "Pictures"),
                str(home / "Videos"),
                str(self.user_data_dir / "assets")
            ])

        return folders

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file, creating defaults if none exist."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings: {e}")

        # Return default settings
        return self._get_default_settings()

    def save_settings(self, settings: Dict[str, Any]):
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error: Could not save settings: {e}")

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings."""
        return {
            "user_data_root": str(self.user_data_dir),
            "output_directory": str(self.output_dir),
            "database_filename": str(self.database_path),
            "library_folders": self.get_default_library_folders(),
            "log_level": "INFO",
            "window_geometry": "",
            "window_state": "",
            "panel_states": {},
            "emotion_analyzer": {
                "face_cascade_path": "",
                "emotion_model_path": str(self.ai_models_dir / "motion-ferplus-8.onnx"),
                "emotion_labels": ["neutral", "happy", "sad", "angry", "surprised"],
                "emotion_input_size": 224,
                "max_frames": 360,
                "face_stride": 3
            },
            # API keys should come from environment variables
            "api_keys": {
                "pixverse": self._get_env_or_prompt("PIXVERSE_API_KEY")
            }
        }

    def _get_env_or_prompt(self, env_var: str) -> str:
        """Get environment variable or return placeholder."""
        return os.environ.get(env_var, f"${{{env_var}}}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        if not self._config_cache:
            self._config_cache = self.load_settings()
        return self._config_cache.get(key, default)

    def set(self, key: str, value: Any):
        """Set a setting value."""
        if not self._config_cache:
            self._config_cache = self.load_settings()
        self._config_cache[key] = value
        self.save_settings(self._config_cache)

    def get_pixverse_api_key(self) -> Optional[str]:
        """Get Pixverse API key from environment or settings."""
        # First try environment variable
        api_key = os.environ.get("PIXVERSE_API_KEY")
        if api_key:
            return api_key

        # Fall back to settings (for backwards compatibility)
        settings = self.load_settings()
        return settings.get("api_keys", {}).get("pixverse")

    def migrate_old_settings(self, old_settings_path: Path):
        """Migrate settings from old location to new user directories."""
        if not old_settings_path.exists():
            return

        try:
            with open(old_settings_path, 'r', encoding='utf-8') as f:
                old_settings = json.load(f)

            # Clean up sensitive data
            if "pixverse_api_key" in old_settings:
                print("Warning: API key found in settings file. Please set PIXVERSE_API_KEY environment variable.")
                del old_settings["pixverse_api_key"]

            # Update paths to new locations
            old_settings["database_filename"] = str(self.database_path)
            old_settings["user_data_root"] = str(self.user_data_dir)
            old_settings["output_directory"] = str(self.output_dir)

            # Save to new location
            self.save_settings(old_settings)

            print(f"Settings migrated from {old_settings_path} to {self.settings_file}")

        except Exception as e:
            print(f"Warning: Could not migrate old settings: {e}")