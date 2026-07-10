---
name: gzh-format
description: Content-factory 自有长文排版入口。Use when the user asks for 公众号排版、微信排版、gzh-format、把 Markdown/OB 长文转公众号 HTML、生成公众号编辑器兼容 HTML、布丁排版、适合布丁的 H5 排版、Markdown 转布丁 HTML、生成预览、维护/新增公众号排版主题或多模板组件库。This skill selects target platform and theme, routes through references/theme-index.md and themes/{id}/components.md, uses scripts/render_markdown.py for deterministic minimal rendering, validates/previews output, and stops before publishing. For creating WeChat drafts delegate to wechat-draft-sync; for Pudding sync delegate to pudding CLI.
---

# GZH Format

你是 `gzh-format` 的入口 skill。**保持薄壳**:只做输入归一、目标平台选择、主题选择、资源加载、产物校验和交付说明;具体排版组件、模板骨架、映射规则都在主题库里。

## 路径约定

`{{skill_root}}` 表示当前 `SKILL.md` 所在目录。所有脚本、主题、样例和引用文件都从该目录解析,因此既可以作为 Content-factory 的子 skill 运行,也可以把本目录单独发布、安装和更新。

## 边界

- 不写稿、不改事实、不发布公众号、不群发。
- 不读取 AppSecret、access_token、cookie、`.env*` 等凭证。
- 不依赖 `.external/gzh-design-skill`;上游只作为收编来源和同步参考。
- 需要创建公众号草稿时,把已校验 HTML 交给 `wechat-draft-sync --html-file`。
- 需要同步布丁管理端可编辑正文时,把源 Markdown 交给 `pudding sync`;不要把公众号/布丁渲染 HTML 写入布丁 `content`。本 skill 不直接调用布丁 API。

## 资源分层

- `references/theme-index.md`:主题路由表和默认选择规则。
- `skill.contract.yaml`:机器可审契约,声明输入、输出、停止点、禁止动作、委托关系、脚本和回归用例。
- `themes/<theme-id>/components.md`:每套主题自己的设计变量、组件 HTML、文章骨架、配方表、Markdown 映射。
- `themes/_shared/common-components.md`:代码块、图片/GIF、素材占位、小标签等跨主题组件。
- `references/format-normalize.md`:非 Markdown 输入归一化规则。
- `references/theme-generator.md`:生成/登记新主题的流程。
- `references/architecture.md`:维护本 skill 架构时读取的分层说明。
- `references/pudding-target.md`:布丁 H5 预览目标的设计边界,以及布丁管理端同步必须用 Markdown 的规则。
- `scripts/render_markdown.py`:默认「简约」主题的确定性 Markdown → HTML 渲染器,支持 `--target wechat|pudding`。
- `scripts/build_pudding_sync_copy.py`:遗留 HTML 同步辅助工具;不要用于布丁管理端可编辑正文。
- `scripts/component_lint.py`:组件库源头检查。
- `scripts/validate_gzh_html.py`:最终 HTML 合规校验。
- `scripts/wrap_preview.py` + `assets/preview-template.html`:生成可复制预览页。
- `scripts/regression.py`:样例回归,串起组件 lint、渲染、产物校验和预览生成。
- `assets/sample-article.md`:演示输入。
- `tests/fixtures/stress-markdown.md`:压力回归输入,覆盖行内语法、列表、表格、引用和分隔线。
- `assets/theme-previews/`:自定义主题生成器的整页区块库预览输出目录。
- `docs/gallery/`:人工浏览主题效果的预览目录。

## 工作流

1. 识别输入:
   - `.md`/Markdown 直接进入主题选择。
   - `.docx`/`.pdf`/纯文本/富文本先读 `references/format-normalize.md` 归一成 Markdown。
   - 没有输入时向用户索要文章路径或内容。
2. 选择目标平台:
   - 用户说“公众号 / 微信 / 草稿箱”时,目标为 `wechat`。
   - 用户说“布丁排版 / 适合布丁 / H5 阅读效果”时,目标为 `pudding`,并读取 `references/pudding-target.md`。
   - 用户没指定时,默认仍为 `wechat`。
3. 选择主题:
   - 必读 `references/theme-index.md`。
   - 用户没指定主题时使用默认主题「简约」(`minimal`)。
   - 用户指定主题时按索引匹配中文名或 `theme-id`。
   - 用户要“生成新主题 / 自定义风格 / 按参考图做一套组件库”时读 `references/theme-generator.md`。
4. 读取组件:
   - 读取索引中选中主题的 `themes/<theme-id>/components.md`。
   - 同时读取 `themes/_shared/common-components.md`。
   - 只用当前主题 + shared 组件,不要跨主题混用。
5. 装配 HTML:
- 默认「简约」主题可直接调用 `scripts/render_markdown.py`。
- 其它主题按所选主题里的“完整文章模板骨架”和“Markdown → 组件映射规则”生成正文片段;需要确定性自动化时新增 renderer adapter,不要改厚主入口。
   - `wechat` 产物从全局 `<section>` 容器开始,不要输出 `<!DOCTYPE>`、`html`、`head`、`body`;所有样式内联;中文文本用 `<span leaf="">...</span>` 包裹。
   - `pudding` 产物从 `<article>` 容器开始,使用正常 H5 语义标签和轻量内联样式;不要输出微信专用 `span leaf`。该产物只用于浏览器预览/未来专用 HTML 字段,不作为 `pudding sync` 的管理端编辑正文输入。
   - 图片 `src` 先保留原文路径/URL;公众号上传和替换交给 `wechat-draft-sync --upload-inline-images`;布丁媒体复制交给 `pudding sync`。
6. 强制校验:

```bash
python3 "{{skill_root}}/scripts/validate_gzh_html.py" "<生成的 HTML 文件>"
```

`validate_gzh_html.py` 只用于 `wechat` target。`pudding` target 用浏览器预览检查视觉效果;同步布丁管理端时对源 Markdown 跑 `pudding sync` dry-run。

7. 生成预览:

```bash
python3 "{{skill_root}}/scripts/wrap_preview.py" "<生成的 HTML 文件>"
```

默认主题的完整命令:

```bash
python3 "{{skill_root}}/scripts/render_markdown.py" "<源 Markdown>" "<输出 HTML>" --theme minimal
```

布丁 H5 目标:

```bash
python3 "{{skill_root}}/scripts/render_markdown.py" "<源 Markdown>" "<输出 HTML>" --theme minimal --target pudding
```

同步布丁管理端可编辑正文:

```bash
pudding sync "<源 Markdown>" --force --type text
```

不要把 `--target pudding` 生成的 HTML 通过临时 Markdown 同步到布丁管理端,否则编辑器会显示 HTML 源码。

## 主题维护规则

- 改某套风格时,只改 `themes/<theme-id>/components.md`;不要把审美细节塞回 `SKILL.md`。
- 新增主题时,新建 `themes/<theme-id>/components.md`,再登记到 `references/theme-index.md`。
- 共用组件改 `themes/_shared/common-components.md`;只有主题确实不同,才在主题组件库里覆盖。
- 改主题后必须跑:

```bash
python3 "{{skill_root}}/scripts/component_lint.py" "{{skill_root}}"
```

## 验收标准

- 主入口仍然是薄壳:流程在 `SKILL.md`,细节在 `themes/` 和 `references/`。
- `component_lint.py` 组件源头 0 ERROR。
- `validate_gzh_html.py` 产物 0 ERROR。
- `regression.py` 能用 `assets/sample-article.md` 和 `tests/fixtures/stress-markdown.md` 跑通默认主题。
- `skillhub doctor-skill skills/gzh-format --profile team` 达到 OK。
- 预览页可复制,复制区域不包含按钮、脚本或预览外壳。
