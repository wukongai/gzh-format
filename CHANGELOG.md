# Changelog

All notable changes to the standalone `gzh-format` distribution are documented here.

## [0.1.0] - 2026-07-10

### Added

- Standalone public repository documentation and installation instructions.
- Root AGPL-3.0-or-later license and third-party attribution notice.
- Thin Agent Skill entry, machine-readable contract, UI metadata, fixtures, and regression workflow.
- Deterministic `minimal` theme renderer for WeChat and Pudding preview targets.
- Local preview wrapper with a copy-to-WeChat action.
- Component lint and final WeChat HTML validation.

### Changed from upstream

- Reorganized theme resources into `themes/<theme-id>/components.md`.
- Made the “简约” theme the default and removed automatic directory/index blocks and decorative separators.
- Clarified that publishing, credentials, image uploads, and platform sync are outside this Skill.

### Known limitations

- Deterministic CLI rendering currently supports only the `minimal` theme.
- `red` and `green` remain Agent-assembled component-library themes until renderer adapters are implemented.
- Remote images and local image paths are preserved but not uploaded.

