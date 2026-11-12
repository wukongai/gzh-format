# gzh-format

把 Markdown 长文排成默认按手机宽度预览、直接改文字与样式、保存并复制到微信公众号编辑器的 HTML。

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

- GitHub 主仓库：[wukongai/gzh-format](https://github.com/wukongai/gzh-format)
- Gitee 国内镜像：[teacherai/gzh-format](https://gitee.com/teacherai/gzh-format)

`gzh-format` 是一个面向 Codex、Claude Code 等 AI Agent 的公众号排版 Skill。你提供 Markdown，它负责主题排版与校验；默认简约主题且来源可可靠映射时,直接交付可编辑、可保存的本机预览页,无需再要求“我要编辑”。

它负责排版、预览、作者直接改稿与本地保存；不代写文章、不读取公众号凭证,也不会自动发布或群发。

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

Agent 会读取 [SKILL.md](skills/gzh-format/SKILL.md) 和主题索引,默认在校验后调用 `wrap_preview.py --editable --source-md` 和 `serve_preview.py`,交付服务 URL。只有明确只读、非 minimal 主题或来源无法可靠映射时,说明只读范围并交付静态预览。此默认行为不授权公众号同步。

## 它解决什么问题

公众号编辑器不能直接理解 Markdown。标题、引用、列表、图片、代码块和表格，需要先转换成微信编辑器能够保留的 HTML 结构和内联样式。

```text
Markdown
  → 选择主题
  → 加载组件与映射规则
  → 序言/一级章节与长普通正文选择原文关键短语（临时工作副本）
  → 生成 HTML
  → 运行微信兼容校验
  → 默认打开可编辑、可保存的本机预览页
  → 作者修改并保存草稿（公众号同步另行确认）
```

## 当前能力

- Markdown → 微信公众号兼容 HTML。
- 所有样式内联，正文文字使用微信兼容的 `span leaf` 包裹。
- 支持标题、段落、加粗、高亮、删除线、下划线、链接、图片、引用、列表、表格和代码块。
- 序言和每个一级章节至少有 1 个红色扫读锚点；120 字以上长普通正文仍各自提炼 1-2 个原文连续短语,原稿和事实不改。
- 默认以 390 CSS px 手机阅读宽度生成预览，窄窗口自动收缩，保留原字号与行距，方便判断文章长度；可编辑页直接在同一正文改稿。
- 可在简约主题预览的受控文字块中改字；工具条支持删除整行、添加当前块类型软换行，选中文字后独立标红/取消红色、加粗/取消粗体，并撤销/重做。
- 点击“保存草稿”直接备份并回填 Markdown、HTML 和 manifest;有未保存修改时每 2 分钟自动保存,保存后仍能撤销/重做并再次保存;无需导出或另存。
- 用确定性脚本检查禁用标签、样式和结构问题。
- 提供固定样例与压力样例回归，修改后可以一键复测。

手机预览指当前电脑浏览器中的手机阅读宽度，不是微信客户端模拟器，也不把本机保存服务开放到手机网络。可保存编辑限于来源可靠映射的简约主题文字块；其它主题、图片、代码、表格等支持范围见[编辑与保存说明](skills/gzh-format/references/editable-preview.md#直接改稿并保存)。直接双击静态 HTML 没有保存服务，需从 Agent 交付的本机服务 URL 打开。

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
  ./gzh-format-sample-preview.html \
  --editable --source-md skills/gzh-format/assets/sample-article.md

python3 skills/gzh-format/scripts/serve_preview.py \
  --manifest ./gzh-format-sample.gzh-edit-manifest.json
```

`--editable` 建立编辑基线,`--source-md` 绑定实际渲染源,serve 的 `--manifest` 指定该基线。打开服务打印的首行 URL 即可编辑并保存；需要手工粘贴时仍可点击“复制到公众号”。在已安装的 Skill 目录内,命令中的 `skills/gzh-format/` 前缀可以省略。

## 在预览中直接保存草稿

只需对 Agent 说“公众号排版这篇 md”,默认即可在效果上改稿并保存。一键发文和公众号同步交付本地排版预览时也共用此默认入口；保存不自动同步微信。

从仓库根目录为已有正文与实际渲染源建立预览,再启动本机服务:

```bash
python3 skills/gzh-format/scripts/wrap_preview.py ./article.html ./article-preview.html \
  --editable --source-md ./article.md

python3 skills/gzh-format/scripts/serve_preview.py \
  --manifest ./article.gzh-edit-manifest.json
```

第一条的两个位置参数为正文 HTML 和预览文件,`--editable` 建立编辑基线,`--source-md` 绑定能确定性重现正文的实际 Markdown。默认在 HTML 同目录生成同名前缀 manifest,其中 `preview_file` 绑定预览路径。源文和输出不能互相别名,已有基线也不能换绑另一预览。

第二条的 `--manifest` 让服务只保存这篇文章。打开 stdout 首行打印的 `http://127.0.0.1:...` 随机 URL,在页面直接改字、删除整行或在光标处添加当前块类型软换行,独立标红/取消红色、加粗/取消粗体。页面有未保存修改时每 2 分钟自动保存一次,也可以点击“保存草稿”立即保存。不下载文件,也无需导出、另存或手工导入。成功后 MD、正文 HTML、manifest 和绑定预览均已保存,每轮有原稿备份。

保存不清当前页撤销/重做历史:删段并保存后,仍可撤销恢复段落,再保存成新修订。保存请求期间可以继续输入,但返回成功只代表触发时的稿已保存,后续输入仍是未保存,由下一轮自动保存或手动保存继续提交。关闭、刷新或重开页面后只保磁盘稿,原 undo 历史不恢复。结束服务按 Ctrl+C,已保存文件保留。

服务默认 `--port 0` 自动选择本机空闲端口;可选 `--ready-file <未存在路径>` 新建 0600 就绪文件,含 URL、origin、pid,不会覆盖已有文件。随机 URL 按本机资源保管,会话 token 不写入正文或 manifest。`file://` 旧预览无法直接保存,保存按钮禁用并提示从本机服务打开。

显式 Markdown 列表项可编辑;图片、代码、表格、双链/嵌入、自动问题组/示例组和固定作者页尾保持只读。H2 章节序号和 H3 标题前缀序号可单独选中、修改或删除，H3 数量和图序仍受保护。来源被其它会话或反向同步改动时拒绝保存,先核对来源再重开服务。已保存人工文字、删除和样式优先,后续不得重新补回红色或粗体。

同步前确认页面最新改稿已保存且没有未保存修改,再运行:

```bash
python3 skills/gzh-format/scripts/preflight_edit.py \
  --manifest ./article.gzh-edit-manifest.json
```

这条命令验证磁盘 `saved` 和 MD/HTML 哈希,不能检测浏览器新输入。本地“保存草稿”只写本机文件,同步公众号仍需另行确认并按三方比较处理。同步成功回写的白名单元数据由 CLI 自动登记,MCP 编排复用共享命令,不提升人工修订号;登记失败时保留已有草稿 ID 和备份,不重复创建。

完整参数、备份、失败处理和[旧包兼容 CLI 附录](skills/gzh-format/references/editable-preview.md#附录旧修改包兼容-cli)见 [编辑与保存说明](skills/gzh-format/references/editable-preview.md)。旧 `.gzh-edit.json` 只用于历史兼容和内部事务记录,不是现行保存步骤。

## 输入与输出

### 输入

- `.md` Markdown 文件。
- 对话中直接提供的 Markdown 文本。
- Word、PDF、富文本等输入需要先按 [格式归一规则](skills/gzh-format/references/format-normalize.md) 转成 Markdown。

### 输出

- 公众号正文 HTML 片段：从顶层 `<section>` 开始，不包含 `html/head/body`。
- 本地预览 HTML：包含预览外壳和复制按钮，复制区域只包含正文。
- 可编辑预览有来源 manifest;保存时在正文同目录 `.gzh-edits/<article_id>/rNNNN-<8hex>/` 归档前后版本及内部事务记录,保留原换行和未编辑片段。
- 校验报告：列出 ERROR、WARN 和微信兼容结构统计。

图片地址会保留原文中的路径或 URL。本 Skill 不上传图片；公众号素材上传应交给独立的草稿同步工具处理。

### 章节与长段落语义锚点兼容说明

“提炼”由 Agent 在临时 Markdown 工作副本中完成：首个 `##` 前的序言和每个 `##` 一级章节至少选择 1 个原文短语；每个不少于 120 个可见字符的长普通正文段落仍要选择 1 个、复杂段落最多 2 个。60-119 字普通段落可以承载章节级锚点。标记写成 `<mark data-gzh="semantic-anchor">原文短语</mark>`。正式排版启用 `--require-semantic-anchors`,renderer 校验章节覆盖、长段漏标、数量、比例和嵌套边界后,确定性输出 `#DC2626` 红色加粗。

未启用覆盖率门禁的旧调用仍按原规则渲染；标题、引用、代码、链接、图片说明、表格、列表和已有行内样式不会被自动处理。账号固定关注语“学习 AI 底层能力和实操干货”在初排时使用原来的自动红色加粗规则。保存人工修订后,显式 `manual-style` 与修订标记保留作者选择,不再为满足初排覆盖率而补红。

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
- 直接保存仅通过浏览器与 `127.0.0.1` 本机服务通信;不上传文章到第三方,不调用外部网络或微信接口。
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

第一条检查组件源头,第二条覆盖排版与共享保存 Python/HTTP 夹具,第三条包含静态分发与完整 Python 回归。仅核对文档或分发静态项时可给第三条加 `--static-only`,但不能据此声称功能回归通过。

修改浏览器编辑或保存行为时,在 `skills/gzh-format/` 目录另跑：

```bash
node --test tests/test_editor_dom.cjs tests/test_editable_e2e.cjs
```

`--test` 运行 DOM 与真实本机 HTTP 端到端用例。执行命令的 Node 必须能解析 `playwright` 模块,并有可用 Chromium/Chrome;复用已有依赖可在命令前设置 `NODE_PATH="<已有 node_modules 目录>"`,浏览器路径可用 `GZH_TEST_BROWSER="<已有浏览器可执行文件>"` 指定。完整范围见[独立夹具验证](skills/gzh-format/references/editable-preview.md#独立夹具验证)。当前本机 SkillHub 没有旧 `lint-skill` / `doctor-skill` 子命令,不能把它们作为通过门禁;项目入口环境巡检另按当前 CLI 帮助执行,不替代本 Skill 验证。

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

### 关掉预览再打开,刚才的改稿就保存了吗？

在本机服务页点击“保存草稿”,等到保存完成且没有未保存修改,磁盘稿才更新。保存后仍能撤销、重做并再次保存;关页重开只恢复磁盘稿,不恢复原撤销历史。`file://` 页不能保存。保存失败保留页面并可重试,未确认结果不算成功;来源冲突时核实来源与归档,不删除 manifest 强行重建,中断遗留锁须确认进程已停后人工处理。

### 可以修改主题吗？

可以。主题规则在 `skills/gzh-format/themes/<theme-id>/components.md`。修改后先跑组件 lint 和回归。

### 可以用它给其它平台做 H5 排版吗？

不可以。公开版只承诺微信公众号 HTML；其它平台应使用各自独立的排版或同步工具。

### 为什么代码是开源的？

这个项目本身来自开源项目的继续改造。公开源码既履行 AGPL 义务，也方便用户安装前审计、学习和按自己的文章风格继续修改。
