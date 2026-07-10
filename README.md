# gzh-format

把 Markdown 长文排成可以预览、校验并复制到微信公众号编辑器的 HTML。

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

- GitHub 主仓库：[wukongai/gzh-format](https://github.com/wukongai/gzh-format)
- Gitee 国内镜像：[teacherai/gzh-format](https://gitee.com/teacherai/gzh-format)

`gzh-format` 是一个给 Codex、Claude Code 等 AI Agent 使用的公众号排版 Skill。你提供一篇 Markdown，它负责读取主题规则、生成公众号兼容 HTML、运行合规检查，并生成带复制按钮的本地预览页。

它只负责排版、预览和校验：不代写文章，不读取公众号凭证，也不会自动发布或群发。

## 它解决什么问题

公众号编辑器不能直接理解 Markdown。标题、引用、列表、图片、代码块和表格，都需要转换成微信编辑器能够保留的 HTML 结构和内联样式。

`gzh-format` 把这段重复流程固化下来：

```text
Markdown
  → 选择主题
  → 加载组件与映射规则
  → 生成 HTML
  → 运行微信兼容校验
  → 生成本地预览页
  → 复制到公众号编辑器
```

## 当前能力

- Markdown → 微信公众号兼容 HTML。
- 所有样式内联，正文文字使用微信兼容的 `span leaf` 包裹。
- 支持标题、段落、加粗、高亮、删除线、下划线、链接、图片、引用、列表、表格和代码块。
- 生成带“复制到公众号”按钮的本地预览页。
- 用确定性脚本检查禁用标签、样式和结构问题。
- 提供固定样例与压力样例回归，修改后可以一键复测。

## 主题状态

| 主题 | ID | 当前状态 | 适合内容 |
|---|---|---|---|
| 简约 | `minimal` | 默认；支持确定性脚本渲染 | 教程、方法论、案例复盘、技术长文 |
| 红色 | `red` | 组件库模式 | 观点、警示、力量感内容 |
| 绿色 | `green` | 组件库模式 | 教程、清单、工具盘点 |

当前 `render_markdown.py` 只承诺 `minimal` 的确定性渲染。`red` 和 `green` 已提供完整组件规则，Agent 可以按规则装配；在对应 renderer adapter 完成前，不把它们宣传成一键脚本主题。

## 快速安装

### 方式一：一行安装

```bash
npx skills add https://github.com/wukongai/gzh-format
```

> [!IMPORTANT]
> 安装 `gzh-format` 不会要求配置 API Key。排版、校验、本地预览和手工复制都不需要微信公众号 AppID/AppSecret。只有以后首次使用独立的“自动创建公众号草稿”工具时，那个工具才会按需引导配置。

这条命令会读取仓库中的 `SKILL.md`，并让你选择安装到支持的 Agent 环境。`npx` 只用于安装，排版运行时不依赖 Node.js。

以下手动安装命令以 GitHub 主仓库为例；如果访问 GitHub 不便，可把仓库地址替换为 `https://gitee.com/teacherai/gzh-format.git`。

### 方式二：手动安装到 Codex

```bash
git clone https://github.com/wukongai/gzh-format.git ~/.agents/skills/gzh-format
```

参数说明：

- `git clone`：把公开仓库复制到本地。
- `~/.agents/skills/gzh-format`：Codex 的用户级 Skill 目录；安装后在新任务中生效。

### 方式三：手动安装到 Claude Code

```bash
git clone https://github.com/wukongai/gzh-format.git ~/.claude/skills/gzh-format
```

如果只想让某个项目使用它，把目标目录换成项目内的 `.agents/skills/gzh-format` 或 `.claude/skills/gzh-format`。项目级安装能避免无关项目加载这个 Skill。

## 更新与停用

如果通过 `npx skills add` 安装，重新运行同一条安装命令即可按安装器提示更新。

如果通过 `git clone` 手动安装，进入安装目录后运行：

```bash
git pull --ff-only
```

`--ff-only` 只接受可以快进的更新；如果你本地修改过主题，它会拒绝覆盖，提醒你先处理自己的改动。

想暂时停用而不是直接删除，可以把目录改名保留备份：

```bash
mv ~/.agents/skills/gzh-format ~/.agents/skills/gzh-format.disabled
```

Claude Code 用户把路径换成 `~/.claude/skills/gzh-format`。改名后重新启动 Agent；确认不再需要本地自定义内容后，再自行删除备份目录。

## 验证安装

进入 Skill 安装目录后运行：

```bash
python3 scripts/regression.py
```

这条命令会依次检查组件库、渲染样例文章、校验公众号 HTML、生成预览页，并跑一份覆盖列表、表格、引用和代码块的压力样例。看到 `regression ok` 说明本地基础能力正常。

运行要求：Python 3.9 或更高版本。脚本只使用 Python 标准库，不需要 `pip install`。

## 直接对 Agent 说

安装完成后，可以这样使用：

```text
用 gzh-format 的简约主题，把 article.md 排成公众号 HTML，并生成预览页。
```

```text
把这篇 Markdown 转成微信公众号兼容 HTML，校验通过后告诉我输出文件位置。
```

```text
先不要发布，只生成一份可以复制到公众号编辑器的本地预览。
```

Agent 会读取 [SKILL.md](SKILL.md) 和主题索引，调用渲染、校验与预览脚本，并停在本地产物交付处。

## 不通过 Agent，直接运行脚本

从仓库根目录执行：

```bash
python3 scripts/render_markdown.py \
  assets/sample-article.md \
  /tmp/gzh-format-sample.html \
  --theme minimal
```

参数说明：

- 第一个路径：输入 Markdown。
- 第二个路径：输出的公众号 HTML。
- `--theme minimal`：选择当前支持确定性渲染的简约主题。

校验输出：

```bash
python3 scripts/validate_gzh_html.py /tmp/gzh-format-sample.html
```

生成带复制按钮的预览页：

```bash
python3 scripts/wrap_preview.py \
  /tmp/gzh-format-sample.html \
  /tmp/gzh-format-sample-preview.html
```

打开 `gzh-format-sample-preview.html`，点击“复制到公众号”，再粘贴到微信公众号编辑器即可。

## 输入与输出

### 输入

- `.md` Markdown 文件。
- 对话中直接提供的 Markdown 文本。
- Word、PDF、富文本等输入需要先按 [格式归一规则](references/format-normalize.md) 转成 Markdown。

### 输出

- 公众号正文 HTML 片段：从顶层 `<section>` 开始，不包含 `html/head/body`。
- 本地预览 HTML：包含预览外壳和复制按钮，复制区域只包含正文。
- 校验报告：列出 ERROR、WARN 和微信兼容结构统计。

图片地址会保留原文中的路径或 URL。本 Skill 不上传图片；公众号素材上传应交给独立的草稿同步工具处理。

## 项目结构

```text
gzh-format/
  README.md
  LICENSE
  THIRD_PARTY_NOTICES.md
  SKILL.md
  skill.contract.yaml
  agents/openai.yaml
  references/
  themes/
    minimal/
    red/
    green/
    _shared/
  scripts/
    render_markdown.py
    validate_gzh_html.py
    component_lint.py
    wrap_preview.py
    regression.py
  assets/sample-article.md
  tests/fixtures/stress-markdown.md
```

- `SKILL.md`：Agent 入口与执行边界。
- `skill.contract.yaml`：输入、输出、停止点和禁止动作。
- `themes/`：主题组件、设计变量和 Markdown 映射。
- `scripts/`：确定性渲染、校验、预览和回归。
- `references/`：主题选择、格式归一、架构和维护规则。

## 隐私与安全

- 本地排版不需要微信公众号 AppID、AppSecret 或 access token。
- 不读取环境变量、AppSecret、access token、cookie、Keychain、`.env` 或其它凭证配置。
- 不请求网络，不上传文章，不把内容发送到第三方服务。
- 不创建公众号草稿，不发布，不群发。
- 所有默认输出都保存在用户指定的本地路径或系统临时目录。

安装任何第三方 Skill 前，都建议先阅读它的 `SKILL.md` 和 `scripts/`。本项目把执行边界写在 [skill.contract.yaml](skill.contract.yaml)，便于人工或工具审计。

## 公众号凭证与自动草稿

先看场景：

| 使用方式 | 是否需要 AppID/AppSecret | 谁负责 |
|---|---:|---|
| 本地排版、校验、生成预览 | 不需要 | `gzh-format` |
| 点击“复制到公众号”后手工粘贴 | 不需要 | 用户浏览器 |
| 自动上传图片并创建公众号草稿 | 需要 | 单独安装的 `wechat-draft-sync` 或同类发布工具 |

因此，安装本仓库后可以立即开始排版，不会弹出凭证配置，也不会因为没有 API Key 而阻塞。

当用户第一次明确要求“自动同步到公众号草稿”时，安全的引导流程应该是：

1. 独立发布工具先运行本地 doctor，只返回 `has_app_id / has_app_secret` 等布尔状态，不显示密钥。
2. 如果缺少配置，工具提示用户在自己的电脑上填写本地凭证文件，而不是把密钥粘贴给 Agent。
3. 默认配置文件位于 `~/.config/wechat-draft-sync/accounts.yaml`，它不在本仓库中。
4. 示例只能使用占位符：

```yaml
default_account: main
accounts:
  main:
    app_id: "<公众号 AppID>"
    app_secret: "<公众号 AppSecret>"
    author: "<作者名>"
```

5. 配置完成后限制文件权限：

```bash
chmod 600 ~/.config/wechat-draft-sync/accounts.yaml
```

`600` 表示只有当前用户可以读取和修改这个文件。

6. 再运行 doctor；通过后先做不联网的 preview/dry-run，检查标题、摘要、封面和正文图片计划。
7. 只有用户明确确认后，发布工具才联网获取 access token、上传图片并创建草稿。
8. AppSecret 如果进入聊天、文章、日志或 Git 历史，应立即在微信公众平台重置，再更新本地配置。

`gzh-format` 不包含自动草稿工具，也不读取它的凭证目录。用户要求自动草稿时，本 Skill 只把已经校验的 HTML 交给单独安装的发布工具。

## 开发与验证

修改主题或 renderer 后，至少运行：

```bash
python3 scripts/component_lint.py .
python3 scripts/regression.py
skillhub lint-skill .
skillhub doctor-skill . --profile team
```

前两条只需要 Python。后两条需要安装可选的 `skillhub`，用于 Agent Skill 结构与工程质量检查。

贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。

维护者发布新版本时的单一真相源与抽仓流程见 [RELEASING.md](RELEASING.md)。

## 来源与许可证

本项目基于 [isjiamu/gzh-design-skill](https://github.com/isjiamu/gzh-design-skill) 继续改造，保留了上游作者甲木（Jiamu）与摸鱼小李（Moyu Xiaoli）的版权声明。

当前版本在上游基础上完成了默认主题重构、薄入口与 contract 分层、确定性 Markdown renderer、压力回归和本地预览链路等修改。完整来源和修改范围见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

本项目以 [GNU AGPL-3.0-or-later](LICENSE) 发布。你可以使用、修改和再分发，但分发修改版本或通过网络提供修改版本时，需要遵守 AGPL 的源码与署名要求。

## 常见问题

### 它会自动发布公众号吗？

不会。它只生成、校验和预览 HTML，发布与草稿同步属于另一个权限更高的流程。

### 为什么不直接把 Markdown 粘贴到公众号？

微信公众号编辑器不会原生解析 Markdown。需要先转换成它能保留的 HTML 标签和内联样式。

### 可以修改主题吗？

可以。主题规则在 `themes/<theme-id>/components.md`。修改后先跑组件 lint 和回归。

### 需要公众号 AppID 或 AppSecret 吗？

不需要。排版、校验、本地预览和手工复制都完全在本地运行。只有另行启用自动草稿同步工具时，那个独立工具才需要本地 BYOK 配置。

### 可以用它给其它平台做 H5 排版吗？

不可以。`v0.2.0` 起公开版只承诺微信公众号 HTML；其它平台应使用各自独立的排版或同步工具。

### 为什么代码是开源的？

这个项目本身来自开源项目的继续改造。公开源码既履行 AGPL 义务，也方便用户安装前审计、学习和按自己的文章风格继续修改。
