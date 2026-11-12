---
title: gzh-format 变更记录
type: changelog
status: active
created: 2026-07-10
updated: 2026-11-12
tags: [公众号, 版本, 变更记录]
related:
  - "[排版入口](SKILL.md)"
  - "[使用说明](README.md)"
---

# Changelog

All notable changes to the standalone `gzh-format` distribution are documented here.

## [0.6.5] - 2026-11-12

### 默认手机阅读宽度预览

- 共享预览模板默认按 390 CSS px 显示正文，窄窗口随屏收缩，保留原字号与行距；只读页与可编辑页使用同一宽度。
- 手机宽度正文直接复用既有标题、文字、删段、样式、保存、撤销/重做和自动保存功能，保存范围与冲突保护保持原合同。
- 窄屏复制栏适配按钮与提示；添加 1100/390/320px 窗口下的直接编辑保存和静态预览回归。
- 发布完整性检查补入标题解析模块及对应测试；本版统一分发此前本地维护的预览编辑、直接保存、自动保存、标题/序号编辑及排版改进。
- 修复 Windows CRLF 正文的来源映射和静态预览偏移，保留源 Markdown 换行、原稿备份及内容冲突保护；跨平台 CI 固定使用支持 Python 3.9 的 Ubuntu 24.04。

> 下列 0.4.x 至 0.6.4 条目是历史本地维护记录，首次统一随 0.6.5 公开分发；历史日期与“本地未发布”描述保留当时状态。

## [0.6.4] - 2026-11-08（本地未发布）

### 开篇引言识别修复

- 简约主题引言保持浅灰底、13px 灰字、默认常规字重与无左侧色条，前置音频播放器或 MP3 占位不再将引言误判成正文观点框。
- 首个一级章节前的 `article-hook` 标记明确映射到轻量引言；正文引用继续使用原样式。
- 已保存的引言取消标红后采用引言灰字，作者显式标红、加粗与文字修改仍保留。
- 补充前置音频、显式引言标记、人工样式与正文引用保真的回归检查；本轮仅本地应用，未提交、推送或发布。

## [0.6.3] - 2026-10-31（本地未发布）

### 章节序号独立编辑

- H2 大号章节序号和 H3 标题前缀序号均可在预览中单独选中、修改或删除，并随现有保存、撤销/重做和两分钟自动保存事务回填。
- H2 改动写入受控 `gzh-h2-number` 标记，空值表示隐藏序号；旧稿仍按原有自动序号渲染，未修改时不把视觉编号写回源文。
- 修复空 H2 序号被通用空块隐藏规则吞掉的问题：编辑态删除后序号行仍可见、可重新输入，预览态继续隐藏空序号。
- 放开 H3 序号前缀保护，仅继续保护 H3 块数量、图片集合和来源冲突；新增 DOM、回填和会话测试。
- 本轮仅本地开发与测试，未提交、推送或发布。

## [0.6.2] - 2026-10-31（本地未发布）

### 可编辑预览自动保存

- 本机保存服务页新增每 2 分钟一次的 dirty-only 自动保存；无修改、输入法组字、已有保存请求或无保存服务时跳过。
- 自动保存复用现有保存事务、快照、manifest、备份、锁和冲突保护；保存期间的新输入继续保持未保存，失败可由下一周期或手动按钮重试。
- 工具条显示自动保存频率与最近一次成功保存时间，手动“保存草稿”继续保留。
- 章节视觉编号绑定到所属 H2 编辑块；点击编号可激活整行操作，添加行改为按当前光标位置插入软换行。
- 手动保存兼容历史 `gzh-manual-revision:v1` 语义锚点：旧稿红标继续保留，新初排内容仍执行句首和泛化引导词门禁。
- 增加自动保存 DOM 回归用例；本轮仅本地开发与测试，未提交、推送或发布。

## [0.6.1] - 2026-10-31（本地未发布）

### 编辑器整行操作与标红收紧

- 新增“删除整行”和“添加一行”工具条操作；正文、H2/H3 与微标题可清空并撤销，添加时保留当前文字样式。
- 保存模型允许作者显式删除 H2/H3；剩余 H3 编号、图片集合和人工修订事务继续受保护。
- renderer 拒绝句首和泛化引导词语义锚点，减少普通句首被误标红；编辑器内标红仍只处理用户选区。
- 增加 DOM、回填和语义锚点边界回归；本轮仅本地开发与测试，未提交、推送或发布。

## [0.5.0] - 2026-10-24（本地未发布）

### 预览人工修订

- 新增唯一共享编辑器,在可可靠映射的简约主题文字块上直接改字、删除,独立标红/取消红色、加粗/取消粗体,并撤销重做。
- `wrap_preview.py --editable --source-md` 绑定实际 Markdown、正文 HTML 与预览路径;无法确定性重现正文时拒绝创建基线。代码、表格、双链/嵌入、自动问题组/示例组和固定作者页尾只读。
- 新增 `serve_preview.py`:单文章 `127.0.0.1` 服务页点击“保存草稿”直接校验、备份并回填 MD/HTML/manifest,无需下载、导出或另存。保存与旧 CLI 共用修订事务,保留原换行和未编辑片段;来源冲突/失败保护继续生效。
- 保存不清当前页撤销/重做历史,删段保存后仍可撤销并再次保存。保存期间新输入仍为未保存;关页重开只保磁盘稿,不保 undo 历史。`file://` 页保存禁用,提示从服务打开;会话 token 不写入正文或 manifest。
- 新增人工样式与修订标记,后续渲染保留作者取消的红色、粗体和删文,不为初排覆盖率重新补红。H3 既有编号从 renderer 源头保留,图序和编号作为导入保护项。
- `preflight_edit.py` 验证 saved 状态、MD/HTML 哈希及已知未导入包;共享接入一键发文和公众号同步,保留作者确认及三方比较,本地保存不授权微信写入。
- 成功同步回写后可用 `--refresh-metadata-from` 登记白名单 frontmatter 变化,默认只校验、apply 后保留人工修订号并刷新来源映射/哈希和绑定预览。写前备份 SHA、当前 HTML、正文和其它元数据严格校验;登记失败保留已创建草稿 ID,不重复 create。

### 验证范围

- 提供独立 Python 回填/渲染/会话/服务夹具和浏览器用例。真实 HTTP＋Chrome 验收通过保存、撤销恢复后保存、重做后保存和重新加载修订3,16图/11个H3编号保真;在途新输入与未确认保存的安全重试另有回归。
- 首轮验收中的下载后导入回填只作为历史证据;当前用户流程已改为直接保存。`import_edit.py` 继续兼容既有包,不再作为主指南步骤。
- 仅本地实现与夹具验证;真实文章另选测试,未执行微信写入、正式发布、提交或推送。静态包检查不代表浏览器、微信端或内容效果认证。

## [0.4.7] - 2026-08-03

### Section-level highlight coverage

- Required the preface and every substantial H2 section to contain at least one semantic scan anchor.
- Allowed 60-119 character ordinary paragraphs to carry section-level anchors while retaining the per-paragraph requirement for 120+ character paragraphs.
- Preserved the 4-18 character phrase limit, two anchors per paragraph, 16% paragraph density, and 8% document density.
- Added regressions for missing section coverage and valid section anchors in medium-length paragraphs.

## [0.4.6] - 2026-08-03

### Long-paragraph highlight coverage

- Required every ordinary paragraph with at least 120 visible characters to carry one or two explicit semantic anchors in the temporary formatting copy.
- Added `--require-semantic-anchors` so the renderer rejects missing long-paragraph highlights without guessing keywords.
- Removed the fixed eight-anchor document cap while retaining per-paragraph and document-wide red-text ratio limits.
- Added regressions for missing coverage and long articles containing more than eight covered paragraphs.

## [0.4.5] - 2026-08-02

### Brand-promise highlight

- Removed the retired trailing `一起吧。` from the rendered author bio, including legacy footer source.
- Changed the fixed brand promise to white bold text on the account-red background with compact inline padding.
- Kept the approved roadmap and contact actions unchanged.

## [0.4.4] - 2026-08-02

### Final author-footer style and link

- Bolded the fixed brand promise in the author bio without splitting the paragraph.
- Updated the two action labels and copy to match the approved WeChat layout.
- Linked the roadmap action to the verified canonical WeChat article URL and rendered it as red bold text with a 1px red underline.
- Kept the footer on the same 8px content baseline and preserved the paste-safe text divider.

## [0.4.3] - 2026-08-02

### Paste-safe END divider

- Replaced the two empty decorative spans around `END` with real thin-line text nodes.
- Prevented WeChat rich-text cleanup from deleting the leading divider after copy/paste.
- Added a regression assertion requiring exactly two non-empty divider lines.

## [0.4.2] - 2026-08-02

### Author footer alignment and actions

- Removed the extra horizontal footer inset and aligned bio/action text with the normal 8px body baseline.
- Split the old inline contact sentence into two deterministic action rows: the AI Native roadmap and the `联系我` entry.
- Kept the roadmap visually link-like without inventing an `href` when no verified public URL is configured.

## [0.4.1] - 2026-07-29

### Author footer

- Added a deterministic author-footer marker contract for WeChat long-form articles.
- Rendered a centered `END` divider followed by one 13px light-gray author paragraph.
- Rejected missing end markers, duplicate blocks, multi-paragraph bios, and author text without the `艾笑：` prefix.

## [0.3.3] - 2026-10-09

### Formatting

- Render copyable AI prompts, commands, scripts, and configuration snippets as code blocks, keeping ordinary quotes and prose in their existing components.
- Convert quote markers only in a temporary formatting copy when a clear copy-and-use introduction identifies the snippet; preserve wording and line order.
- Add a mixed prompt, command, and ordinary-quote regression fixture.

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
