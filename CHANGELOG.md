# Changelog

All notable changes to the standalone `gzh-format` distribution are documented here.

## [0.3.2] - 2026-07-11

### Evaluation compatibility

- Stopped presenting the human-readable installation record as a machine-verifiable JSON behavior report after newer skillhub production doctor versions introduced `EVAL107` validation.
- Kept the record as declared, non-certified evidence and preserved the explicit boundary:structural readiness is not downstream content utility.

## [0.3.1] - 2026-07-11

### Windows compatibility

- Configured every Python CLI entry to emit UTF-8 safely, preventing `UnicodeEncodeError` when Windows runners or user terminals default to legacy `cp1252` output.
- Added the shared console helper to the required release bundle and verified the full release check under a simulated `PYTHONIOENCODING=cp1252` environment.

## [0.3.0] - 2026-07-11

### Installation and compatibility

- Moved the installable bundle to the standard `skills/gzh-format/` catalog layout so `npx skills add wukongai/gzh-format` copies scripts, themes, fixtures, and licenses together.
- Made `npx skills add` the primary cross-Agent installation path; retained Git clone only as a manual download and audit fallback.
- Added clean-copy installation regression for Codex and Claude Code instead of accepting an installer's success message alone.
- Documented the exact verified compatibility scope instead of claiming support for every Agent Skills client.
- Added Agent Skills `license`, `compatibility`, author, and version metadata.

### Validation and portability

- Added an offline release checker for required files, relative links, secret-like content, absolute user paths, Python syntax, and functional regression.
- Made regression outputs use the operating system temporary directory instead of hard-coding `/private/tmp`.
- Added assertions that copy controls and scripts stay in the preview shell and never enter WeChat body HTML.
- Added Ubuntu, macOS, and Windows CI for Python 3.9 and 3.14.

## [0.2.1] - 2026-07-11

### Documentation

- Moved the credential boundary next to installation: installing `gzh-format` never requires an API key.
- Added a scenario matrix distinguishing local formatting, manual copy, and separately installed automatic draft sync.
- Documented the safe first-use handoff: local credential file, redacted doctor, dry-run, explicit confirmation, and secret rotation after leakage.

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
