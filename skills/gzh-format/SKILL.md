---
name: gzh-format
description: 微信公众号长文排版 Skill。Use when the user asks for 公众号排版、微信排版、gzh-format、把 Markdown/OB 长文转为公众号编辑器兼容 HTML、生成本地预览、维护/新增公众号排版主题或多模板组件库。It routes through references/theme-index.md and themes/{id}/components.md, uses scripts/render_markdown.py for deterministic minimal rendering, validates/previews output, and stops before draft creation or publishing. Do not use for Pudding/H5 formatting, article writing, or platform publishing.
license: AGPL-3.0-or-later
metadata:
  author: wukongai
  version: "0.3.1"
  compatibility: Requires Python 3.9+ and local filesystem access. Runtime formatting needs no network access or credentials.
---

# GZH Format

你是 `gzh-format` 的入口 skill。保持薄壳:只做输入归一、主题选择、资源加载、公众号 HTML 装配、校验和本地预览;具体组件、模板骨架和映射规则放在主题库。

## 路径约定

`{{skill_root}}` 表示当前 `SKILL.md` 所在目录。所有脚本、主题、样例和引用文件都从该目录解析,因此既可作为 Content-factory 子 skill 运行,也可独立安装和更新。

## 边界

- 只生成微信公众号兼容 HTML,不提供 Pudding/H5 等其它平台 target。
- 不写稿、不改事实、不创建公众号草稿、不发布、不群发。
- 本地排版、校验和预览不需要 AppID、AppSecret 或 access token。
- 不读取环境变量、`.env*`、Keychain、cookie 或 `~/.config/wechat-draft-sync/`。
- 用户只需手工复制到公众号编辑器时,不得要求其配置或提交任何凭证。
- 用户明确要求自动创建公众号草稿时,把已校验 HTML 交给独立 `wechat-draft-sync`;凭证检查和微信 API 调用不在本 skill 内执行。

## 资源分层

- `references/theme-index.md`:主题路由表和默认选择规则。
- `skill.contract.yaml`:输入、输出、停止点、禁止动作、委托关系、脚本和回归用例。
- `themes/<theme-id>/components.md`:每套主题的变量、组件 HTML、文章骨架、配方和 Markdown 映射。
- `themes/_shared/common-components.md`:代码块、图片/GIF、素材占位和小标签等共用组件。
- `references/format-normalize.md`:非 Markdown 输入归一化规则。
- `references/theme-generator.md`:生成和登记新主题的流程。
- `references/architecture.md`:维护本 skill 架构时读取的分层说明。
- `scripts/render_markdown.py`:默认「简约」主题的确定性 Markdown → 公众号 HTML 渲染器。
- `scripts/component_lint.py`:组件库源头检查。
- `scripts/validate_gzh_html.py`:公众号 HTML 合规校验。
- `scripts/wrap_preview.py` + `assets/preview-template.html`:生成可复制预览页。
- `scripts/regression.py`:样例和压力回归。

## 工作流

1. 识别输入:
   - `.md`/Markdown 直接进入主题选择。
   - `.docx`/`.pdf`/纯文本/富文本先读 `references/format-normalize.md` 归一成 Markdown。
   - 没有输入时向用户索要文章路径或内容。
2. 选择主题:
   - 必读 `references/theme-index.md`。
   - 用户没指定时使用默认主题「简约」(`minimal`)。
   - 用户指定主题时按索引匹配中文名或 `theme-id`。
   - 用户要生成新主题或按参考图做组件库时读 `references/theme-generator.md`。
3. 读取组件:
   - 读取 `themes/<theme-id>/components.md` 与 `themes/_shared/common-components.md`。
   - 只使用当前主题和 shared 组件,不要跨主题混用。
4. 装配公众号 HTML:
   - 默认「简约」主题调用 `scripts/render_markdown.py`。
   - 其它主题按组件库的完整骨架和映射规则装配;需要确定性自动化时新增 renderer adapter。
   - 产物从顶层 `<section>` 开始,不输出 `<!DOCTYPE>`、`html`、`head`、`body`;所有样式内联;中文文本用 `<span leaf="">` 包裹。
   - 图片 `src` 保留原文路径或 URL;本 skill 不上传图片。
5. 强制校验:

```bash
python3 "{{skill_root}}/scripts/validate_gzh_html.py" "<生成的 HTML 文件>"
```

6. 生成预览:

```bash
python3 "{{skill_root}}/scripts/wrap_preview.py" "<生成的 HTML 文件>"
```

默认主题完整命令:

```bash
python3 "{{skill_root}}/scripts/render_markdown.py" "<源 Markdown>" "<输出 HTML>" --theme minimal
```

## 主题维护规则

- 改某套风格时只改 `themes/<theme-id>/components.md`。
- 新增主题时新建主题目录,再登记到 `references/theme-index.md`。
- 共用组件改 `themes/_shared/common-components.md`。
- 改主题后运行:

```bash
python3 "{{skill_root}}/scripts/component_lint.py" "{{skill_root}}"
```

## 验收标准

- `SKILL.md` 保持接口和路由层,审美细节留在 `themes/` 与 `references/`。
- `component_lint.py` 0 ERROR。
- `validate_gzh_html.py` 0 ERROR。
- `regression.py` 跑通公众号样例和压力样例,并确认旧 `--target pudding` 被拒绝。
- `skillhub doctor-skill skills/gzh-format --profile commercial` 为 OK。
- 预览页可复制,复制区域不包含按钮、脚本或预览外壳。
