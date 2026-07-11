# gzh-format

把 Markdown 长文排成可以预览、校验并复制到微信公众号编辑器的 HTML。

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

- GitHub 主仓库：[wukongai/gzh-format](https://github.com/wukongai/gzh-format)
- Gitee 国内镜像：[teacherai/gzh-format](https://gitee.com/teacherai/gzh-format)

`gzh-format` 是一个面向 Codex、Claude Code 等 AI Agent 的公众号排版 Skill。你提供 Markdown，它负责读取主题规则、生成公众号兼容 HTML、运行合规检查，并生成带复制按钮的本地预览页。

它只负责排版、预览和校验：不代写文章，不读取公众号凭证，也不会自动发布或群发。

## 快速安装

电脑需要安装 Node.js/npm，用它运行通用 Skill 安装器；Skill 安装完成后的排版运行时只需要 Python 3.9+，不需要 `pip install`。

```bash
npx skills add wukongai/gzh-format
```

这条命令会识别仓库中的 `skills/gzh-format/` 完整包，并让你选择 Agent 和项目级或用户级安装位置。脚本、主题、样例、测试与许可证会一起复制，不只是 `SKILL.md`。

常用的无交互安装方式：

```bash
# Codex：安装到用户级 Skill 目录
npx skills add wukongai/gzh-format --skill gzh-format -g -a codex -y

# Claude Code：安装到用户级 Skill 目录
npx skills add wukongai/gzh-format --skill gzh-format -g -a claude-code -y
```

参数说明：

- `--skill gzh-format`：只安装仓库中的这个 Skill。
- `-g`：用户级安装；不加时由安装器选择或安装到当前项目。
- `-a codex` / `-a claude-code`：指定目标 Agent。
- `-y`：接受本次安装选项，适合自动化和回归测试。

> [!IMPORTANT]
> 安装和使用 `gzh-format` 不需要公众号 API Key。排版、校验、本地预览和手工复制都不需要 AppID/AppSecret。只有另行启用“自动创建公众号草稿”工具时，那个独立工具才会引导你在本机配置凭证。

### GitHub 不可用时

可以从 Gitee 安装：

```bash
npx skills add https://gitee.com/teacherai/gzh-format.git --skill gzh-format
```

如果安装器无法访问远程仓库，使用手动备用流程：

```bash
git clone --depth 1 https://gitee.com/teacherai/gzh-format.git gzh-format
npx skills add ./gzh-format/skills/gzh-format
```

`git clone` 只负责下载源码；第二条命令才把完整 Skill 安装到目标 Agent。不要把整个仓库根目录直接克隆成 `gzh-format` 的 Skill 目录，因为可安装包位于 `skills/gzh-format/`。

## 验证安装

用户级安装后，可在对应目录运行回归：

```bash
python3 ~/.agents/skills/gzh-format/scripts/regression.py
```

当前安装器默认把用户级共享副本放在 `~/.agents/skills/gzh-format`，再暴露给指定 Agent。看到 `regression ok` 说明脚本、主题、样例和预览链路都已完整安装。不同版本或客户端的目录可能不同；如果安装器显示了其它目标目录，请在它给出的 `gzh-format` 目录下运行 `python3 scripts/regression.py`。

## 直接对 Agent 说

安装完成后，新建一个 Agent 任务并说：

```text
用 gzh-format 的简约主题，把 article.md 排成公众号 HTML，并生成预览页。
```

也可以说：

```text
把这篇 Markdown 转成微信公众号兼容 HTML，校验通过后告诉我输出文件位置。先不要发布。
```

Agent 会读取 [SKILL.md](skills/gzh-format/SKILL.md) 和主题索引，调用渲染、校验与预览脚本，并停在本地产物交付处。

## 它解决什么问题

公众号编辑器不能直接理解 Markdown。标题、引用、列表、图片、代码块和表格，需要先转换成微信编辑器能够保留的 HTML 结构和内联样式。

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

## 更新与卸载

查看并更新已安装 Skill：

```bash
npx skills list -g
npx skills update gzh-format -g -y
```

卸载：

```bash
npx skills remove gzh-format -g -y
```

更新前如果修改过本地主题，请先备份对应目录，避免安装器替换本地定制内容。

## 不通过 Agent，直接运行脚本

从仓库根目录运行：

```bash
python3 skills/gzh-format/scripts/render_markdown.py \
  skills/gzh-format/assets/sample-article.md \
  ./gzh-format-sample.html \
  --theme minimal

python3 skills/gzh-format/scripts/validate_gzh_html.py ./gzh-format-sample.html

python3 skills/gzh-format/scripts/wrap_preview.py \
  ./gzh-format-sample.html \
  ./gzh-format-sample-preview.html
```

打开 `gzh-format-sample-preview.html`，点击“复制到公众号”，再粘贴到微信公众号编辑器即可。在已安装的 Skill 目录内，命令中的 `skills/gzh-format/` 前缀可以省略。

## 输入与输出

### 输入

- `.md` Markdown 文件。
- 对话中直接提供的 Markdown 文本。
- Word、PDF、富文本等输入需要先按 [格式归一规则](skills/gzh-format/references/format-normalize.md) 转成 Markdown。

### 输出

- 公众号正文 HTML 片段：从顶层 `<section>` 开始，不包含 `html/head/body`。
- 本地预览 HTML：包含预览外壳和复制按钮，复制区域只包含正文。
- 校验报告：列出 ERROR、WARN 和微信兼容结构统计。

图片地址会保留原文中的路径或 URL。本 Skill 不上传图片；公众号素材上传应交给独立的草稿同步工具处理。

## 已验证的兼容范围

| 范围 | 结果 | 验证方式 |
|---|---|---|
| `npx skills add` 完整包安装 | 通过 | 新目录安装后检查脚本、主题、样例并运行回归 |
| Codex 用户级 / 项目级目录 | 通过 | `skills` CLI 安装 + 回归 |
| Claude Code 用户级 / 项目级目录 | 通过 | `skills` CLI 安装 + 回归 |
| Python 3.9 | 通过 | Python 3.9.6 完整回归 |
| Python 3.14 | 通过 | Python 3.14.5 完整回归 |
| 其它 Agent Skills 客户端 | 结构兼容，未逐个运行 | 需按客户端文档确认 Skill 发现和脚本权限 |

仓库的 GitHub Actions 在 Ubuntu、macOS、Windows 上分别用 Python 3.9 和 3.14 运行同一套离线发布检查。只有对应提交的 CI 全绿，才应扩大操作系统兼容承诺。

## 项目结构

```text
gzh-format/
  README.md
  LICENSE
  THIRD_PARTY_NOTICES.md
  .github/workflows/release-check.yml
  skills/
    gzh-format/
      SKILL.md
      skill.contract.yaml
      LICENSE
      THIRD_PARTY_NOTICES.md
      agents/openai.yaml
      references/
      themes/
      scripts/
      assets/
      tests/
```

仓库根目录放产品文档与 CI；`skills/gzh-format/` 是安装器复制的完整运行包。许可证和第三方声明在两层都保留，确保用户只安装 Skill 包时仍能看到授权与来源。

## 隐私与安全

- 本地排版不需要微信公众号 AppID、AppSecret 或 access token。
- 不读取环境变量、AppSecret、access token、cookie、Keychain、`.env` 或其它凭证配置。
- 不请求网络，不上传文章，不把内容发送到第三方服务。
- 不创建公众号草稿，不发布，不群发。
- 所有默认输出都保存在用户指定的本地路径或系统临时目录。

安装任何第三方 Skill 前，都建议先阅读它的 [SKILL.md](skills/gzh-format/SKILL.md) 和脚本。本项目把执行边界写在 [skill.contract.yaml](skills/gzh-format/skill.contract.yaml)，便于人工或工具审计。

## 公众号凭证与自动草稿

| 使用方式 | 是否需要 AppID/AppSecret | 谁负责 |
|---|---:|---|
| 本地排版、校验、生成预览 | 不需要 | `gzh-format` |
| 点击“复制到公众号”后手工粘贴 | 不需要 | 用户浏览器 |
| 自动上传图片并创建公众号草稿 | 需要 | 单独安装的 `wechat-draft-sync` 或同类发布工具 |

安装本仓库后可以立即开始排版，不会弹出凭证配置，也不会因为没有 API Key 而阻塞。

当用户第一次明确要求“自动同步到公众号草稿”时，独立发布工具应在用户本机完成凭证 doctor 和配置引导，只报告是否缺少配置，不把 AppSecret 打印到聊天或日志。`gzh-format` 不包含自动草稿工具，也不读取它的凭证目录。

## 开发与验证

修改主题或 renderer 后，从仓库根目录运行：

```bash
python3 skills/gzh-format/scripts/component_lint.py skills/gzh-format
python3 skills/gzh-format/scripts/regression.py
python3 skills/gzh-format/scripts/release_check.py
```

可选的 `skillhub` 检查：

```bash
skillhub lint-skill skills/gzh-format
skillhub doctor-skill skills/gzh-format --profile team
```

贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)，发布流程见 [RELEASING.md](RELEASING.md)。

## 来源与许可证

本项目基于 [isjiamu/gzh-design-skill](https://github.com/isjiamu/gzh-design-skill) 继续改造，保留了上游作者甲木（Jiamu）与摸鱼小李（Moyu Xiaoli）的版权声明。

当前版本在上游基础上完成了默认主题重构、薄入口与 contract 分层、确定性 Markdown renderer、压力回归、本地预览链路和标准 Skill 分发目录。完整来源和修改范围见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

本项目以 [GNU AGPL-3.0-or-later](LICENSE) 发布。你可以使用、修改和再分发，但分发修改版本或通过网络提供修改版本时，需要遵守 AGPL 的源码与署名要求。

## 常见问题

### 它会自动发布公众号吗？

不会。它只生成、校验和预览 HTML，发布与草稿同步属于另一个权限更高的流程。

### 需要公众号 AppID 或 AppSecret 吗？

不需要。只有另行启用自动草稿同步工具时，那个独立工具才需要本地配置。

### 可以修改主题吗？

可以。主题规则在 `skills/gzh-format/themes/<theme-id>/components.md`。修改后先跑组件 lint 和回归。

### 可以用它给其它平台做 H5 排版吗？

不可以。公开版只承诺微信公众号 HTML；其它平台应使用各自独立的排版或同步工具。

### 为什么代码是开源的？

这个项目本身来自开源项目的继续改造。公开源码既履行 AGPL 义务，也方便用户安装前审计、学习和按自己的文章风格继续修改。
