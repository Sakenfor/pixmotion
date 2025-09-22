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

## Scan profile defaults

`ScanProfileService` seeds a `scan_profiles.json` file in the user data root.
Installations created before this release may still reference the legacy
`person_detected` tag in the `deep_pass` filter, which the quick pass never
produced. On startup the service now replaces the file when it matches the old
defaults so the `deep_pass` profile filters for the actual `portrait`/`animal`
tags. If you customised the profile definitions, remove the obsolete
`person_detected` entry manually (or delete the file to let the defaults be
recreated) to pick up the new behaviour.
