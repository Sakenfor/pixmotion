# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Prompt Enhancer Plugin**: New plugin that enhances video generation prompts using AI Hub models
  - Integrates seamlessly with the existing Pixverse Generator Panel
  - Supports multiple AI providers (OpenAI, Anthropic, Local, Offline)
  - Offers 5 enhancement styles: Creative, Descriptive, Cinematic, Atmospheric, Technical
  - Uses existing AI Hub service infrastructure to avoid code duplication
  - Features threaded processing to maintain UI responsiveness
  - Includes comprehensive integration tests
  - Files added:
    - `plugins/prompt_enhancer/plugin.json` - Plugin manifest
    - `plugins/prompt_enhancer/plugin.py` - Main plugin registration
    - `plugins/prompt_enhancer/services.py` - Core enhancement service
    - `plugins/prompt_enhancer/widgets.py` - UI components
    - `plugins/prompt_enhancer/extension.py` - Generator Panel integration
    - `plugins/prompt_enhancer/test_integration.py` - Integration tests

### Changed
- **Generator Panel**: Extended to emit initialization event for plugin integration
  - Modified `plugins/generation/panels.py` to publish "generator_panel_initialized" event
  - No breaking changes to existing functionality

### Technical Details
- Follows established plugin architecture patterns from `docs/PLUGIN_DEVELOPMENT.md`
- Uses dependency injection through the service registry
- Implements proper error handling and user feedback
- Maintains code consistency with existing UI patterns
- Ensures no duplication of AI Hub or provider management functionality

## [Previous Versions]

_Note: This changelog was created as part of the Prompt Enhancer plugin implementation. Previous version history would be documented here in a real project._