# PixMotion

A powerful desktop application for AI-powered video generation using the Pixverse API. PixMotion provides an intuitive interface for creating videos from images with advanced emotion analysis and asset management capabilities.

## 🌟 Features

- **AI Video Generation**: Create videos from images using the Pixverse API
- **Asset Management**: Organize and browse your images and videos with thumbnails
- **Emotion Analysis**: AI-powered emotion detection in video content
- **Tag System**: Hierarchical tagging system for organizing assets
- **Cross-Platform**: Runs on Windows, macOS, and Linux
- **Plugin Architecture**: Extensible plugin system for custom functionality

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- PyQt6
- Pixverse API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd pixmotion
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   ```bash
   # Windows
   set PIXVERSE_API_KEY=your_api_key_here

   # macOS/Linux
   export PIXVERSE_API_KEY=your_api_key_here
   ```

   Or create a `.env` file in the project root:
   ```
   PIXVERSE_API_KEY=your_api_key_here
   ```

4. **Run the application:**
   ```bash
   python run_app.py
   ```

## 📁 Directory Structure

After first run, PixMotion creates the following directories in appropriate OS locations:

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

## 🎨 User Interface

### Main Window
The main window consists of several dockable panels:

- **Asset Browser**: Browse and manage your image and video files
- **Generator Panel**: Configure and create AI-generated videos
- **Graph Explorer**: Visual workflow editor (advanced users)

### Asset Browser
- Import images and videos by scanning folders
- Generate thumbnails automatically
- Rate assets and add tags
- Search and filter your media library

### Video Generation
1. Select an input image from the Asset Browser
2. Enter a descriptive prompt for your video
3. Choose generation settings (model, quality, duration)
4. Click "Generate" to create your video
5. Generated videos are automatically saved and added to your library

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PIXVERSE_API_KEY` | Your Pixverse API key | Required |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |

### Settings File

Settings are stored in `settings.json` in the configuration directory. Key settings:

- `library_folders`: Directories to scan for assets
- `output_directory`: Where generated videos are saved
- `log_level`: Application logging level
- `emotion_analyzer`: Emotion analysis configuration

## 🔌 Plugin Development

PixMotion uses a modular plugin architecture. See [PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) for detailed development documentation.

### Creating a Plugin

1. Create a new directory in `plugins/`
2. Add `plugin.json` manifest file
3. Implement `plugin.py` with your plugin class
4. Register services, UI components, and commands

Example plugin structure:
```
plugins/my_plugin/
├── plugin.json
├── plugin.py
├── services/
└── ui/
```

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

Or run individual test files:
```bash
python -m unittest tests.test_config_manager
python -m unittest tests.test_framework
```

## 🛠️ Troubleshooting

### Common Issues

**Application won't start:**
- Check that all dependencies are installed
- Verify Python version (3.8+ required)
- Check console output for error messages

**API key errors:**
- Ensure `PIXVERSE_API_KEY` environment variable is set
- Verify your API key is valid and has sufficient credits
- Check network connectivity

**Database errors:**
- Delete the database file to reset: `{UserData}/PixMotion/pixmotion.db`
- Check file permissions in the user data directory

**Plugin errors:**
- Check plugin dependencies in `plugin.json`
- Review plugin logs in the application log file
- Ensure plugin follows the correct interface

### Log Files

Application logs are saved to:
- **Windows**: `%LOCALAPPDATA%\PixMotion\logs\pixmotion.log`
- **macOS**: `~/Library/Caches/PixMotion/logs/pixmotion.log`
- **Linux**: `~/.cache/PixMotion/logs/pixmotion.log`

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Documentation Index](docs/README.md)** - Start here for complete documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)** - Understand the system design
- **[Plugin Development](docs/PLUGIN_DEVELOPMENT.md)** - Create custom functionality
- **[API Reference](docs/API_REFERENCE.md)** - Service and interface documentation
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## 🆘 Support

- **Issues**: Report bugs and request features on GitHub Issues
- **Documentation**: Check the `docs/` directory for detailed guides
- **Community**: Join our community discussions

## 🙏 Acknowledgments

- Pixverse team for the AI video generation API
- PyQt team for the excellent desktop framework
- Contributors and community members

---

**Note**: This software is not affiliated with or endorsed by Pixverse. Please ensure you comply with Pixverse's terms of service when using their API.