# Third-party notices

## Upstream project

`gzh-format` is based on:

- Project: `gzh-design-skill`
- Repository: <https://github.com/isjiamu/gzh-design-skill>
- Copyright: © 2026 甲木（Jiamu）× 摸鱼小李（Moyu Xiaoli）
- License: GNU Affero General Public License v3.0 or later

The upstream copyright and license notice are preserved in [LICENSE](LICENSE).

## Resources adapted from upstream

The following parts were imported, reorganized, or modified from the upstream project:

- `themes/red/components.md`
- `themes/green/components.md`
- `themes/_shared/common-components.md`
- `themes/minimal/components.md`, adapted from the upstream “橄榄手记” theme
- `references/format-normalize.md`
- `references/theme-generator.md`
- `references/eval-cases.md`
- `scripts/component_lint.py`
- `scripts/render_markdown.py`
- `scripts/validate_gzh_html.py`
- `scripts/wrap_preview.py`
- `assets/preview-template.html`

## Main modifications in gzh-format

- Rebuilt the root `SKILL.md` as a thin workflow and resource router.
- Reorganized theme assets under `themes/<theme-id>/components.md`.
- Added `skill.contract.yaml` for machine-reviewable inputs, outputs, stops, delegates, and forbidden actions.
- Made `minimal` the default theme and changed its title, quote, image, list, and spacing rules.
- Added deterministic Markdown rendering for the `minimal` theme.
- Added a Pudding-oriented semantic H5 preview target without making Pudding a runtime dependency.
- Added stress fixtures and a regression runner covering inline syntax, lists, tables, quotes, code blocks, and preview generation.
- Added standalone installation, privacy, contribution, security, and release documentation.

More detailed adoption notes are maintained in [references/gzh-design-adoption.md](references/gzh-design-adoption.md).

## License scope

The standalone `gzh-format` distribution is released under GNU AGPL-3.0-or-later. No additional restriction is added to the rights granted by that license.

