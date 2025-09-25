"""Tests for the ConfigManager class."""

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from framework.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager functionality."""

    def setUp(self):
        """Set up test environment."""
        self.config_manager = ConfigManager()

    @patch('platform.system')
    @patch('os.environ')
    def test_windows_paths(self, mock_environ, mock_system):
        """Test that Windows paths are set correctly."""
        mock_system.return_value = 'Windows'
        mock_environ.get.side_effect = lambda key, default='': {
            'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming',
            'USERPROFILE': 'C:\\Users\\Test',
            'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'
        }.get(key, default)

        config_manager = ConfigManager()

        self.assertEqual(
            str(config_manager.config_dir),
            'C:\\Users\\Test\\AppData\\Roaming\\PixMotion'
        )
        self.assertEqual(
            str(config_manager.user_data_dir),
            'C:\\Users\\Test\\Documents\\PixMotion'
        )
        self.assertEqual(
            str(config_manager.cache_dir),
            'C:\\Users\\Test\\AppData\\Local\\PixMotion'
        )

    @patch('platform.system')
    def test_macos_paths(self, mock_system):
        """Test that macOS paths are set correctly."""
        mock_system.return_value = 'Darwin'

        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/Users/test')
            config_manager = ConfigManager()

            self.assertEqual(
                str(config_manager.config_dir),
                '/Users/test/Library/Application Support/PixMotion'
            )
            self.assertEqual(
                str(config_manager.user_data_dir),
                '/Users/test/Documents/PixMotion'
            )

    @patch('platform.system')
    def test_linux_paths(self, mock_system):
        """Test that Linux paths are set correctly."""
        mock_system.return_value = 'Linux'

        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/home/test')
            config_manager = ConfigManager()

            self.assertEqual(
                str(config_manager.config_dir),
                '/home/test/.config/PixMotion'
            )

    def test_default_settings(self):
        """Test that default settings are generated correctly."""
        settings = self.config_manager._get_default_settings()

        self.assertIn('user_data_root', settings)
        self.assertIn('output_directory', settings)
        self.assertIn('database_filename', settings)
        self.assertIn('library_folders', settings)
        self.assertIn('emotion_analyzer', settings)
        self.assertIsInstance(settings['library_folders'], list)

    @patch.dict(os.environ, {'PIXVERSE_API_KEY': 'test_key_123'})
    def test_get_pixverse_api_key_from_env(self):
        """Test that API key is retrieved from environment variable."""
        api_key = self.config_manager.get_pixverse_api_key()
        self.assertEqual(api_key, 'test_key_123')

    @patch.dict(os.environ, {}, clear=True)
    def test_get_pixverse_api_key_fallback(self):
        """Test API key fallback to settings when env var not set."""
        with patch.object(self.config_manager, 'load_settings') as mock_load:
            mock_load.return_value = {
                'api_keys': {'pixverse': 'settings_key_456'}
            }
            api_key = self.config_manager.get_pixverse_api_key()
            self.assertEqual(api_key, 'settings_key_456')

    def test_migrate_old_settings(self):
        """Test migration of old settings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            old_settings = {
                'pixverse_api_key': 'old_key_789',
                'database_filename': 'old.db',
                'some_setting': 'value'
            }
            json.dump(old_settings, f)
            old_path = Path(f.name)

        try:
            with patch.object(self.config_manager, 'save_settings') as mock_save:
                self.config_manager.migrate_old_settings(old_path)

                # Should have called save_settings
                mock_save.assert_called_once()

                # Get the settings that were passed to save_settings
                saved_settings = mock_save.call_args[0][0]

                # API key should be removed
                self.assertNotIn('pixverse_api_key', saved_settings)

                # Other settings should be preserved
                self.assertIn('some_setting', saved_settings)
                self.assertEqual(saved_settings['some_setting'], 'value')

        finally:
            # Clean up
            old_path.unlink()

    def test_settings_file_property(self):
        """Test that settings file path is correct."""
        expected_path = self.config_manager.config_dir / "settings.json"
        self.assertEqual(self.config_manager.settings_file, expected_path)

    def test_database_path_property(self):
        """Test that database path is correct."""
        expected_path = self.config_manager.user_data_dir / "pixmotion.db"
        self.assertEqual(self.config_manager.database_path, expected_path)


if __name__ == '__main__':
    unittest.main()