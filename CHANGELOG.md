# Changelog

All notable changes to the standalone `gzh-format` distribution are documented here.

## [0.2.0] - 2026-07-11

### Breaking changes

- Removed the Pudding/H5 render target, output contract, renderer branch, reference, helper script, and regression assertions.
- Removed `--target`; the CLI now has one output contract: WeChat Official Account compatible HTML.
- Calls that still pass `--target pudding` fail with an explicit argparse error and must migrate to a platform-specific tool.

### Security and boundaries

- Clarified that formatting, validation, local preview, and manual copy require no AppID, AppSecret, or access token.
- `gzh-format` does not read environment variables, credential files, Keychain, cookies, or another tool's configuration.
- Automatic draft creation remains delegated to a separately installed credentialed publishing tool such as `wechat-draft-sync`.

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
