# Configuration Management

PixMotion uses a sophisticated configuration system that provides OS-appropriate paths, hierarchical settings, and plugin-specific configuration. This document covers all aspects of configuration management.

## Configuration Overview

The configuration system consists of several layers:

1. **Application Settings** - Core application configuration in `app_settings.json`
2. **Environment Variables** - Sensitive data and system-specific settings
3. **User Data Management** - OS-appropriate paths for data storage
4. **Plugin Configuration** - Plugin-specific settings and preferences

## File Locations

PixMotion follows OS conventions for configuration and data storage using the `ConfigManager`:

### Windows
- **Configuration**: `%APPDATA%\PixMotion\`
- **User Data**: `%USERPROFILE%\Documents\PixMotion\`
- **Cache**: `%LOCALAPPDATA%\PixMotion\`

### macOS
- **Configuration**: `~/Library/Application Support/PixMotion/`
- **User Data**: `~/Documents/PixMotion/`
- **Cache**: `~/Library/Caches/PixMotion/`

### Linux
- **Configuration**: `~/.config/PixMotion/`
- **User Data**: `~/Documents/PixMotion/`
- **Cache**: `~/.cache/PixMotion/`

## User Data Root

The application persists caches, generated media, and plugin data beneath a configurable **user data root**. The root is controlled via the `user_data_root` entry in `app_settings.json` and is resolved by the core `SettingsService`.

- When the value is **relative**, it is interpreted relative to the project root (for example, the default value `"data"` resolves to `<project>/data`).
- Absolute values can be used to redirect all persistent assets to another drive.

Use `SettingsService.resolve_user_path(*parts)` to build paths inside this root. The helper normalizes separators, honors absolute overrides, and creates the target directory (or its parent when resolving files).

### Usage Tips

- Plugins that need to store files should append to the shared root instead of calling `framework.get_project_root()` directly.
- Relative settings such as `output_directory`, model caches, or scan profiles can now omit the `data/` prefix—`resolve_user_path("generated_media")` resolves to the correct location automatically.
- When referencing files bundled with the application (for example, packaged models), keep using explicit paths; `resolve_user_path` is intended for user-generated content and caches.

## Settings Service

The Settings Service provides a high-level interface for configuration management:

### Interface

```python
from interfaces import ISettingsService

class ISettingsService(IService):
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value using dot notation."""
        pass

    def set(self, key: str, value: Any):
        """Set a setting value using dot notation."""
        pass

    def resolve_user_path(self, *parts: str, ensure_exists: bool = True) -> str:
        """Resolve a path relative to user data directory."""
        pass
```

### Usage Examples

```python
settings = framework.get_service("settings_service")

# Get/set simple values
theme = settings.get("ui.theme", "dark")
settings.set("ui.theme", "light")

# Get/set nested values
api_key = settings.get("ai_providers.openai.api_key")
settings.set("ai_providers.openai.enabled", True)

# Path resolution
output_dir = settings.resolve_user_path("generated_videos")
config_file = settings.resolve_user_path("plugins", "my_plugin", "config.json")
```

### Dot Notation Support

The settings service supports dot notation for nested configuration access:

```python
# Instead of this:
config = settings.get("ai_providers")
openai_config = config.get("openai", {})
model = openai_config.get("model", "default")

# Use this:
model = settings.get("ai_providers.openai.model", "default")
```

## Environment Variables

Sensitive configuration data should be stored in environment variables:

### Required Environment Variables

```bash
# Pixverse API key (required for video generation)
PIXVERSE_API_KEY=your_pixverse_api_key_here

# Optional AI provider keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_AI_API_KEY=your_google_api_key_here

# Optional configuration overrides
LOG_LEVEL=DEBUG
PIXMOTION_DATA_DIR=/custom/data/path
```

### Environment Variable Loading

PixMotion automatically loads environment variables from `.env` files:

```bash
# .env file in project root
PIXVERSE_API_KEY=sk-1234567890abcdef
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-abcdef1234567890
```

## Application Settings

The main configuration file `app_settings.json` contains core application settings:

```json
{
    "database": {
        "url": "sqlite:///pixmotion.db",
        "echo": false,
        "create_tables": true
    },
    "user_data_root": "data",
    "log_level": "INFO",
    "ui": {
        "theme": "dark",
        "window_geometry": {
            "x": 100,
            "y": 100,
            "width": 1200,
            "height": 800
        }
    },
    "pixverse": {
        "api_endpoint": "https://api.pixverse.ai/v1",
        "default_model": "pixverse-v1",
        "timeout": 300
    },
    "ai_providers": {
        "openai": {
            "enabled": true,
            "model": "gpt-4-vision-preview",
            "max_tokens": 150,
            "temperature": 0.1
        }
    },
    "asset_management": {
        "supported_image_formats": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"],
        "supported_video_formats": [".mp4", ".avi", ".mov", ".mkv", ".webm"],
        "thumbnail_size": [256, 256],
        "auto_generate_thumbnails": true
    },
    "tag_layers": {
        "auto_process_new_assets": true,
        "default_confidence_threshold": 0.7,
        "batch_processing_size": 10
    }
}
```

## Plugin Configuration

Plugins can define their own configuration schemas and access settings through the settings service:

### Accessing Plugin Configuration

```python
class MyPluginService(IService):
    def initialize(self):
        settings = self.framework.get_service("settings_service")

        # Get plugin-specific configuration with defaults
        self.config = settings.get("plugins.my_plugin", {
            "enabled": True,
            "processing_mode": "batch",
            "batch_size": 50
        })

        # Update configuration
        self.config["last_run"] = datetime.now().isoformat()
        settings.set("plugins.my_plugin", self.config)
```

### Plugin Settings Storage

Plugin settings are automatically stored in the appropriate user data directory and persist across application restarts.

## Scan Profile Defaults

The `ScanProfileService` seeds a `scan_profiles.json` file in the user data root. Installations created before recent releases may still reference legacy tags in filter configurations. On startup, the service automatically replaces outdated profile files with current defaults to ensure compatibility with current AI analysis capabilities.

If you have customized profile definitions, remove obsolete entries manually or delete the file to let the defaults be recreated.

## Configuration Best Practices

### For Plugin Developers

1. **Use Settings Service**: Always access configuration through the settings service
2. **Provide Defaults**: Define sensible defaults for all configuration values
3. **Validate Settings**: Validate configuration values before use
4. **Use resolve_user_path()**: For any file storage needs within user data
5. **Environment Variables**: Use environment variables for sensitive data

### For Users

1. **Backup Configuration**: Keep backups of `app_settings.json` before major changes
2. **Environment Variables**: Set sensitive API keys as environment variables
3. **Path Configuration**: Use absolute paths for custom data directories if needed
4. **Log Levels**: Use DEBUG log level only when troubleshooting

This configuration system ensures consistent, secure, and OS-appropriate management of all application and plugin settings.