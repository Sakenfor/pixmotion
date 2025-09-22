# Configuration Guide

## User Data Root

The application persists caches, generated media, and plugin data beneath a
configurable **user data root**. The root is controlled via the
`user_data_root` entry in `app_settings.json` and is resolved by the core
`SettingsService`.

* When the value is **relative**, it is interpreted relative to the project
  root (for example, the default value `"data"` resolves to
  `<project>/data`).
* Absolute values can be used to redirect all persistent assets to another
  drive.

Use `SettingsService.resolve_user_path(*parts)` to build paths inside this
root. The helper normalises separators, honours absolute overrides, and
creates the target directory (or its parent when resolving files).

### Usage tips

* Plugins that need to store files should append to the shared root instead of
  calling `framework.get_project_root()` directly.
* Relative settings such as `output_directory`, model caches, or scan profiles
  can now omit the `data/` prefix—`resolve_user_path("generated_media")`
  resolves to the correct location automatically.
* When referencing files bundled with the application (for example, packaged
  models), keep using explicit paths; `resolve_user_path` is intended for
  user-generated content and caches.
