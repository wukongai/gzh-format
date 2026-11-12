---
title: gzh-format 架构说明
type: reference
status: active
created: 2026-07-07
updated: 2026-10-28
tags: [公众号, 架构, 预览编辑]
related:
  - "[排版入口](../SKILL.md)"
  - "[机器合同](../skill.contract.yaml)"
---

# gzh-format 架构说明

`gzh-format` 采用“一个入口、内部分层”的 skill 架构:

```text
gzh-format/
  README.md                        # 对外产品说明、安装和快速开始
  LICENSE                         # AGPL-3.0-or-later 完整许可证
  THIRD_PARTY_NOTICES.md          # 上游来源、版权和本地修改说明
  CHANGELOG.md                    # 独立发行版本记录
  CONTRIBUTING.md                 # 贡献主题、脚本和文档的流程
  SECURITY.md                     # 安全边界和漏洞报告方式
  RELEASING.md                    # 单一真相源、发布前检查和 subtree 抽仓流程
  SKILL.md                         # 唯一全局入口,只写流程和边界
  skill.contract.yaml              # 机器可审契约,声明输入/输出/停止点/禁忌/脚本/测试
  references/
    theme-index.md                 # 主题路由表
    mode-index.md                  # 内容模式路由表
    format-normalize.md            # 非 Markdown 输入归一化
    theme-generator.md             # 新主题生成与登记
    architecture.md                # 本文件
    editable-preview.md            # 编辑、保存与同步前检查合同
  themes/
    _shared/common-components.md   # 跨主题共用组件
    minimal/components.md          # 默认主题:简约
    red/components.md              # 红色
    green/components.md            # 绿色高密度主题
  modes/
    ai-daily/mode.md               # AI 日报公众号正文契约
    ai-daily/template.md           # AI 日报公众号正文骨架
  scripts/
    render_markdown.py             # 默认主题确定性公众号 HTML 渲染器
    component_lint.py              # 组件库源头关
    validate_gzh_html.py           # 产物关
    wrap_preview.py                # 预览外壳
    serve_preview.py               # 单文章本机 HTTP 预览与直接保存
    edit_model.py                  # source-map、修改包、修订归档和冲突保护
    import_edit.py                 # 默认 dry-run、显式 apply 回填
    preflight_edit.py              # 已保存修订预检与成功同步元数据登记
    regression.py                  # 样例回归
  assets/
    sample-article.md              # 演示输入
    editor.js / editor.css         # 两上游共用的浏览器编辑器与工具栏
    theme-previews/                # 主题生成器预览输出
  docs/gallery/                    # 人工浏览主题效果
  tests/fixtures/                  # 回归夹具
    ai-daily-markdown.md           # AI 日报模式回归
    stress-markdown.md             # 压力回归:行内语法/列表/表格/引用/分隔线
  tests/test_editable_preview.py   # 独立本地回填和冲突保护夹具
  tests/test_editor_dom.cjs        # 选区、直接保存状态、保存后撤销及file协议边界
  tests/test_edit_session.py       # 稳定文字块会话、保存后撤销恢复与冲突保护
  tests/test_save_service.py       # 本机单文章服务、同源会话与直接保存保护
```

## 职责边界

- `SKILL.md`:触发、输入输出、主题选择、校验命令、禁止项。
- `README.md`:给第一次接触本项目的用户阅读,负责产品介绍、安装、使用和常见问题;不承载 agent 执行规则。
- `LICENSE` / `THIRD_PARTY_NOTICES.md`:明确 AGPL 许可、上游作者版权和本地修改边界。
- `skill.contract.yaml`:给 skillhub 和 agent 读取的机器契约,避免复杂 skill 靠口头上下文运行。
- `references/theme-index.md`:主题名、标识、适用场景、组件库路径。
- `references/mode-index.md`:内容模式、自动命中条件和模式规则路径;模式与主题正交。
- `themes/<id>/components.md`:具体设计变量、组件 HTML、文章骨架、配方、Markdown 映射。
- `modes/<id>/`:某类内容独有的输入门禁、文章骨架和语义映射;不复制主题视觉变量。
- `themes/_shared/common-components.md`:代码块、图片、素材占位等所有主题都可复用的基础组件。
- `scripts/`:确定性渲染、source-map、语义标记门禁、受控回填、同步前检查和回归验证。
- `assets/`:示例输入和主题生成器预览资产。
- `tests/fixtures/`:真实或压力回归样例,用于防止 Markdown 映射和样式约束回退。

## 维护原则

- 改视觉风格,只改对应主题的 `components.md`。
- 改主题选择,只改 `theme-index.md`。
- 改内容骨架或专属语义,改 `mode-index.md` 与对应 `modes/<id>/`,不要复制整套主题。
- 改通用组件,只改 `_shared/common-components.md`。
- 新增主题是加目录和登记索引,不是改厚主入口。
- 新增确定性渲染能力时,给主题加 renderer adapter,或扩展 `render_markdown.py`;不要把模板逻辑写进 `SKILL.md`。其它平台能力应拆成独立 skill,不在本入口增加 target。
- 改主题后先跑 `component_lint.py`,生成产物后再跑 `validate_gzh_html.py`。
- 改 renderer / contract / 回归用例后,在 Skill 目录运行 `python3 scripts/release_check.py`,覆盖静态分发与完整 Python/HTTP 回归;`--static-only` 只做静态检查。改浏览器编辑/保存还须运行 `node --test tests/test_editor_dom.cjs tests/test_editable_e2e.cjs`,环境要求见[共享验证说明](editable-preview.md#独立夹具验证)。当前 SkillHub 不提供旧 `lint-skill` / `doctor-skill`;入口软链巡检不作为本 Skill 功能通过门禁。

## 跨主题语义契约

- 长段落“提炼”属于 skill 编排层:只从原普通正文段落选择连续原文短语,写入临时 Markdown 工作副本;不得修改用户原稿或改写句子。
- 中间标记固定为 `<mark data-gzh="semantic-anchor">原文短语</mark>`。renderer 不做语义猜测,只校验并映射为 `<strong style="color:#DC2626;font-weight:800;">…</strong>`。
- 首个 `##` 前的序言和每个 `##` 一级章节,只要存在不少于 60 个可见字符的可选普通正文段落,至少使用 1 个锚点;复杂章节可分散选择 2-3 个。
- 每个不少于 120 个可见字符的长普通正文段落仍必须使用 1 个、复杂段落最多 2 个锚点;单短语 4-18 个可见字符,单段占比 ≤16%,全文不设固定数量上限但总占比 ≤8%。
- 标题、引用、代码、链接、图片/图注、表格、列表和已有行内样式范围不允许语义锚点。账号固定关注语继续走独立自动规则,不重复套标记。
- 未启用覆盖率门禁的旧调用保持原渲染行为;正式初排启用 `--require-semantic-anchors`,人工修订优先于初排覆盖率,不得自动补红。
- 开篇引言的视觉容器已经表达引用语义,各主题不应再自动添加首尾装饰引号。
- 多行开篇引言允许换行,但 Markdown 引用中的空白行必须折叠;相邻非空行之间最多输出一次换行。
- 非开篇引用仍由各主题自行选择引号、竖线或卡片样式,不受开篇引言契约影响。
- 新增 renderer adapter 时,必须用 fixture 同时覆盖“无装饰引号”和“无双换行”。
- 新增 renderer adapter 时,还必须覆盖语义锚点的章节漏标、长段漏标、60 字以下段落误标、单段数量/全文比例、结构区误用、嵌套冲突和旧调用兼容。

## 人工修订的共享边界

编辑能力只在 gzh-format 实现一次。一键发文引导作者审阅与保存,wechat-draft-sync 管理同步授权、三方比较和微信 API;两者调用共享本机预览、直接保存和预检,不复制编辑器。`import_edit.py` 只保留历史包兼容。

### 预览工具条布局

[共享编辑样式](../assets/editor.css)控制 `#gzh-editor-toolbar`，采用 `position:sticky;top:66px;z-index:98`。工具条直属 `body`，与正文区域并列；[预览外壳](../assets/preview-template.html)的复制栏固定在顶部，高 54px、层级 99，编辑条在其下方留出 12px 间距。窄屏保留 flex 自动换行。编辑条位于 `#gzh-content` 之外，复制仅克隆正文；打印样式继续隐藏编辑条。

[本机预览服务](../scripts/serve_preview.py)每次 GET 通过 [预览装配器](../scripts/wrap_preview.py)重新读取并内嵌共享 CSS，响应设置 `Cache-Control: no-store`；运行服务使用当前共享目录时，刷新会取得新样式。已打开页面中的未保存输入不会自动迁移，先保存再刷新；静态预览文件需要重新包装。作者操作统一见[直接改稿并保存](editable-preview.md#直接改稿并保存)。

### 修订数据与保存

renderer 提供 source-map,`edit_model.py` 只开放可靠映射的段落、H2/H3、引用、显式 Markdown 列表项及 micro 标题。双链/嵌入、代码、表格、固定作者页尾、自动问题组/示例组等无法确定性回填的组件只读。H2 视觉序号和 H3 标题前缀序号可单独回填；图片集合/顺序与 H3 数量是修订保存保护项。

manifest 记录本地来源与 `preview_file` 路径、MD/HTML 哈希、文字块、保护项和事务指纹。源 MD、正文、manifest、预览的路径别名在写入前拒绝,含 symlink;已绑定预览路径不能另换。`gzh-edit/v1` 只作内部传输、归档与历史兼容,不是用户导出步骤;页面没有导出/另存按钮,不依赖 localStorage。

`serve_preview.py` 只监听 `127.0.0.1`,随机端口/会话 URL 绑定一篇文章,准确 Host/Origin 与会话 token 校验通过才接受同源保存。HTTP 不接收源文件路径,token 不写 manifest/文章正文;可选新建的 0600 ready-file 仅含 url/origin/pid。服务不调用微信或外网,file 协议页没有保存能力。

直接保存与兼容 CLI 共用 `compose_package` / `commit_revision`,在文章级锁内校验并于 `.gzh-edits/<article_id>/rNNNN-<8hex>/` 归档前后稿、基线与内部事务包。失败尝试恢复 MD/HTML/manifest/绑定预览并留 `failed.txt`;中断锁人工核实进程停止后处理。`EditSession` 保留稳定文字块身份,支持删段→保存→撤销恢复→再保存;页面保存不清 undo/redo,在途新输入仍 dirty。重开页或服务只恢复磁盘稿,不恢复浏览器历史;来源被反向同步/其它会话改动时拒绝保存,核对后重开服务。

`manual-style` span 保存独立 red/bold,文章修订标记使初排覆盖率让位于作者选择。上游不得重新补红、恢复删文或清理标记。同步前确认页面最新稿无未保存修改,再验证磁盘 saved 与哈希;旧兼容包仍按已知目录检查。磁盘预检不能检测浏览器新输入,不替代三方比较,本地保存不授权微信同步。参数与失败路径见 [editable-preview.md](editable-preview.md)。

同步成功后的 frontmatter 回写会改变源 SHA,因此共享预检提供 `--refresh-metadata-from <本次写前备份>`。备份须匹配旧源 SHA,当前 HTML、正文及非白名单元数据须不变;只接受 digest、wechat_draft_media_id、wechat_draft_synced_at、wechat_draft_status、wechat_draft_title、wechat_thumb_media_id。默认只校验,apply 后保留人工 revision/已导入包记录,重建 source-map 与源哈希并刷新绑定预览。CLI 成功 writeback 后自动调用,MCP 编排复用;普通预检结果用 `manifest_file` 标识基线。登记失败不能再 create,先保留已创建草稿 ID/备份并处理冲突;此入口不用于绕过正文冲突。
