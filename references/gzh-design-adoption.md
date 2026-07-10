---
title: gzh-design-skill 收编说明
type: reference
status: active
created: 2026-07-07
updated: 2026-07-07
tags: [wechat, gzh-design, license, 公众号排版]
related:
  - "[[../SKILL]]"
---

# gzh-design-skill 收编说明

上游仓库:`https://github.com/isjiamu/gzh-design-skill`

## 当前决策

`gzh-format` 已改造成 Content-factory 自有的多主题公众号排版 skill:

- `SKILL.md` 是唯一全局入口,只写流程、边界和资源路由。
- `references/theme-index.md` 是主题路由表。
- `themes/<theme-id>/components.md` 存放每套主题的组件、模板骨架和映射规则。
- `themes/_shared/common-components.md` 存放跨主题通用组件。
- `scripts/component_lint.py` 做组件库源头检查。
- `scripts/render_markdown.py` 做默认「简约」主题的确定性渲染。
- `scripts/validate_gzh_html.py` 做最终 HTML 产物检查。
- `scripts/wrap_preview.py` 和 `assets/preview-template.html` 生成可复制预览页。
- `scripts/regression.py` 串联样例回归。
- 运行时不需要 `.external/gzh-design-skill`。

## 已收编资源

以下资源来源于上游 `gzh-design-skill`,并在本 skill 内继续维护:

- `themes/red/components.md`（由上游红色编辑风主题本地重命名为「红色」）
- `themes/green/components.md`（由上游绿色杂志风主题本地重命名为「绿色」）
- `themes/_shared/common-components.md`
- `references/format-normalize.md`
- `references/theme-generator.md`
- `references/eval-cases.md`
- `scripts/component_lint.py`
- `scripts/render_markdown.py`
- `scripts/validate_gzh_html.py`
- `scripts/wrap_preview.py`
- `assets/preview-template.html`

`themes/minimal/components.md` 由上游「橄榄手记」主题改造而来,按本账号当前审美重命名为「简约」并作为默认主题。

## 本地改造要点

- 主 skill 从单主题说明改为薄壳入口。
- 主题从 `references/theme-*.md` 迁移到 `themes/<theme-id>/components.md`。
- 默认主题改为「简约」(`minimal`)。
- 主题列表收敛为「简约 / 红色 / 绿色」三套;移除与简约风格重叠较高的极简、留白、票据主题。
- 「简约」主章节标题采用数字在上、标题在下、左对齐的结构,去掉 `PART`、英文标签、竖线和底部分隔线。
- 开篇引用改成浅灰底小字双引号块,不再使用强封面卡/编者按卡。
- 去掉“本文看点 / INDEX / 目录卡片”这类自动导读结构。
- 图片边框改轻,和正文文字左右对齐。
- 列表改为轻量短横线 `-`,字号与行距更紧。
- 默认不主动给关键词加下划线;只保留源文显式下划线语义。
- 分割线/分割点默认禁用,章节之间靠标题上下留白。

## 许可证边界

上游许可证为 AGPL-3.0。完整许可证文本保存在仓库根:

- `LICENSE`

工程含义:

- 可以把上游资源收编成本地 skill,但必须保留来源与许可证说明。
- 后续如果继续同步/改造上游组件,仍需更新本文件的“已收编资源”和“本地改造要点”。
- “自己的 skill”在这里指 Content-factory 自己维护、自己默认调用、自己承担风格演进;不表示抹除上游作者版权。
