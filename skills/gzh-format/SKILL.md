---
name: gzh-format
description: 微信公众号长文与 AI 日报专属排版 Skill。Use when the user asks for 公众号排版、微信排版、gzh-format、把 Markdown/OB 长文转为公众号 HTML、生成或直接编辑本地排版预览、保存预览人工改稿、维护公众号排版主题或内容模式。Do not use for Pudding/H5 formatting, article writing, or platform publishing.
title: 公众号排版与预览人工修订
type: skill
status: active
created: 2026-07-07
updated: 2026-11-12
tags: [公众号, 排版, 人工修订]
related:
  - "[编辑与保存合同](references/editable-preview.md)"
license: AGPL-3.0-or-later
metadata:
  author: wukongai
  version: "0.6.5"
  compatibility: Requires Python 3.9+ and local filesystem access. Formatting needs no external network or credentials; direct saving uses a loopback HTTP service.
---

# GZH Format

你是 `gzh-format` 的入口 skill。保持薄壳:只做输入归一、主题与内容模式选择、公众号 HTML 装配、校验、本地预览与作者人工修订保存;组件和映射留在主题库与模式库,编辑合同见 [editable-preview.md](references/editable-preview.md)。

## 路径约定

`{{skill_root}}` 表示当前 `SKILL.md` 所在目录。所有脚本、主题、样例和引用文件都从该目录解析,因此既可作为 Content-factory 子 skill 运行,也可独立安装和更新。

## 边界

- 只生成微信公众号兼容 HTML,不提供 Pudding/H5 等其它平台 target。
- 不写稿、不改事实;长段落提炼只从原文选择短语做样式标记,不得摘要、改写或补充观点。
- 作者在本机服务预览中直接改字、删除内容,独立控制红色与粗体,点击“保存草稿”或等待每 2 分钟自动保存真正回填 Markdown/HTML 并备份;保存后仍可撤销/重做,无需导出或另存。
- 预览正文上方显示可编辑标题框，标题与正文一起保存，同步时消费保存的标题；标题来源、已有唯一 H1 的维护、旧包兼容及复杂 YAML 限制见编辑合同。
- 不创建公众号草稿、不发布、不群发。
- 本地排版、校验和预览不需要 AppID、AppSecret 或 access token。
- 不读取环境变量、`.env*`、Keychain、cookie 或 `~/.config/wechat-draft-sync/`。
- 用户只需手工复制到公众号编辑器时,不得要求其配置或提交任何凭证。
- 用户明确要求自动创建公众号草稿时,把已校验 HTML 交给独立 `wechat-draft-sync`;凭证检查和微信 API 调用不在本 skill 内执行。

## 资源分层

- `references/theme-index.md`:主题路由表和默认选择规则。
- `references/mode-index.md`:内容模式路由表;模式决定文章骨架和专属语义,不改变主题配色。
- `skill.contract.yaml`:输入、输出、停止点、禁止动作、委托关系、脚本和回归用例。
- `themes/<theme-id>/components.md`:每套主题的变量、组件 HTML、文章骨架、配方和 Markdown 映射。
- `themes/_shared/common-components.md`:代码块、图片/GIF、素材占位和小标签等共用组件。
- `modes/ai-daily/mode.md` + `template.md`:AI 日报公众号正文的输入门禁、固定骨架、视觉映射和新稿模板。
- `references/format-normalize.md`:非 Markdown 输入归一化规则。
- `references/theme-generator.md`:生成和登记新主题的流程。
- `references/architecture.md`:维护本 skill 架构时读取的分层说明。
- `references/editable-preview.md`:本机预览、直接保存、会话历史、备份、人工样式与同步前检查;旧包 CLI 留在兼容附录。
- `scripts/render_markdown.py`:默认「简约」主题的确定性 Markdown → 公众号 HTML 渲染器。
- `scripts/component_lint.py`:组件库源头检查。
- `scripts/validate_gzh_html.py`:公众号 HTML 合规校验。
- `scripts/wrap_preview.py` + `assets/preview-template.html`:生成可复制或可编辑预览页;编辑逻辑共享 `assets/editor.js` / `editor.css`。
- `scripts/serve_preview.py`:只绑定一篇文章的本机 HTTP 预览与“保存草稿”入口。
- `scripts/edit_model.py`、`preflight_edit.py`:共享修订事务、稳定块会话和同步前检查;`import_edit.py` 只保留旧包兼容 CLI。
- `scripts/article_title.py`:标题纯文字解析、受控回填及复杂 YAML 只读边界。
- `scripts/regression.py`:样例和压力回归。

## 工作流

1. 识别输入:
   - `.md`/Markdown 直接进入主题与内容模式选择。
   - `.docx`/`.pdf`/纯文本/富文本先读 `references/format-normalize.md` 归一成 Markdown。
   - 没有输入时向用户索要文章路径或内容。
2. 选择主题:
   - 必读 `references/theme-index.md`。
   - 用户没指定时使用默认主题「简约」(`minimal`)。
   - 用户指定主题时按索引匹配中文名或 `theme-id`。
   - 用户要生成新主题或按参考图做组件库时读 `references/theme-generator.md`。
3. 选择内容模式:
   - 必读 `references/mode-index.md`。
   - 普通长文使用 `default`;frontmatter/文件名命中 AI 日报公众号正文时使用 `ai-daily`。
   - `ai-daily` 必须继续读取 `modes/ai-daily/mode.md`;新建正文时复用同目录 `template.md`。
   - 原始 `YYYYMMDD-AI日报.md` 不是公众号正文,停止并要求上游先准备 `YYYYMMDD-AI日报-公众号正文.md`。
4. 读取组件:
   - 读取 `themes/<theme-id>/components.md` 与 `themes/_shared/common-components.md`。
   - 只使用当前主题和 shared 组件,不要跨主题混用。
5. 章节扫读锚点与长段落提炼:
   - **先查人工修订**:源文已有 `<!-- gzh-manual-revision:v1 -->` 或显式 `data-gzh="manual-style"` 时,读取编辑合同并保留作者文字、删除和独立样式;不得重新挑选语义锚点、补红或恢复已删除内容。以下覆盖率要求仅用于初次排版。
   - 在**不修改用户原稿**的前提下生成临时工作副本;把首个 `##` 前的正文视为序言,再按每个 `##` 划分一级内容大块。
   - 序言或一级章节只要存在不少于 60 个可见字符、可放锚点的普通正文段落,整块至少选择 1 个关键短语;复杂章节可分散选择 2-3 个,但不要求每个中短段落都标红。
   - 每个达到 120 个可见字符的长普通正文仍必须各自选择 1 个、复杂段落最多 2 个关键短语;60-119 字普通段落允许承载章节级锚点。
   - 标题、引用、代码、链接文字、图片/图注、表格、列表、已有 `**加粗**` / `==高亮==` / `<u>` / `++下划线++` / `~~删除线~~` 都不自动提炼。
   - 每个锚点都必须从原句中原样选取 4-18 字短语;单段最多 2 个,锚点不超过段落可见字符的 16%,全文标红总占比不超过 8%。锚点不得位于段首或句首,不得以“因此/同时/如果/通过/我们/可以/需要”等泛化引导词开头;无法独立表达判断时宁可不标。
   - 选中的原文短语用 `<mark data-gzh="semantic-anchor">原文短语</mark>` 标记。禁止改字、换序、拼接不连续文本或把整句/整段包入标记。初次排版 renderer 会拒绝句首和泛化引导词锚点,不要等到预览后再靠人工擦除；已有 `gzh-manual-revision:v1` 人工修订稿会保留历史红标以保证保存兼容。
   - 不选择已经带行内语义的范围,也不重复标记账号固定关注语“学习 AI 底层能力和实操干货”。
6. 装配公众号 HTML:
   - 开篇引言使用当前主题的轻量引言组件；简约主题固定为浅灰底加灰色小字。音频播放器或占位在前时仍按引言识别，不套用正文注释框；细节见组件14。
   - 先按 shared 组件库“一、代码块组件”的可复制内容规则检查 AI 提示词、操作命令和配置。需要从引用改成围栏代码块时只改临时工作副本的标记,原文措辞和行序保持不变;普通引言、观点和章节过渡仍按引用渲染。
   - 默认「简约」主题初次排版调用 `scripts/render_markdown.py --require-semantic-anchors`;无人工修订时,序言/一级章节完全无锚点或长段落漏标,返回第 5 步补齐。人工修订标记使覆盖率门禁让位于作者样式。
   - 其它主题按组件库的完整骨架和映射规则装配;需要确定性自动化时新增 renderer adapter。
   - renderer 只消费上一步的显式语义标记,确定性映射为 `#DC2626` 红色加粗;不得在最终 HTML 上做关键词猜测或随机替换。
   - 源文出现唯一一组 `<!-- gzh-author-footer:start -->` / `<!-- gzh-author-footer:end -->` 时,按简约主题组件36渲染固定 `END`、作者介绍和两条联系动作;标记内必须恰好一个以 `艾笑：` 开头的自然段。`END` 两侧使用真实细线文本,不依赖会被公众号粘贴清洗删除的空装饰节点。页尾文字与普通正文使用同一 8px 内容基线,不额外收窄;品牌承诺句固定为红底白色粗体,末尾不再追加“一起吧。”,进阶地图使用已核验的公众号文章主链接与红色粗体下划线样式。
   - 产物从顶层 `<section>` 开始,不输出 `<!DOCTYPE>`、`html`、`head`、`body`;所有样式内联;中文文本用 `<span leaf="">` 包裹。
   - 图片 `src` 保留原文路径或 URL;本 skill 不上传图片。
   - H2 章节序号和 H3 标题前缀序号都是独立可编辑文字；可以选中、修改或删除并随正文保存。图片集合和顺序、H3 数量仍为保存保护项。
7. 强制校验:

```bash
python3 "{{skill_root}}/scripts/validate_gzh_html.py" "<生成的 HTML 文件>"
```

8. 默认交付可编辑、可保存的手机宽度预览:

普通公众号排版和 AI 日报的 `minimal` 确定性排版完成后,默认读取 [编辑与保存说明](references/editable-preview.md),建立编辑基线并启动本机保存服务。作者只说“公众号排版”也执行此流程,不要求再补“我要编辑”。

默认正文按 390 CSS px 手机阅读宽度显示，窄窗口自动收缩；在这份预览中直接编辑，不另开宽屏编辑页。这个宽度用于判断换行和文章长度，不缩放字号，也不代表微信客户端像素级还原；服务仍运行在当前电脑。

```bash
python3 "{{skill_root}}/scripts/wrap_preview.py" "<正文 HTML>" "<预览 HTML>" --editable --source-md "<实际渲染 Markdown>"
```

`--editable` 开启共享编辑器与基线 manifest;`--source-md` 必须指向能确定性重现此 HTML 的实际工作副本。可用 `--manifest <路径>` 指定基线文件,默认 `<HTMLstem>.gzh-edit-manifest.json`。预览路径绑定到 manifest 的 `preview_file`,省略输出时复用已绑定路径;不能另换路径或与源 MD/正文/manifest 指向同一文件。只支持可确定性映射的 `minimal`;不猜测旧 HTML 的来源。可编辑正文段落、H2/H3、引用、显式 Markdown 列表项和 micro 标题;含双链/图片语法的块、代码、表格、自动问题组/示例组和固定作者页尾保持只读。

接着启动本机服务,把它打印的首行 URL 作为默认验收入口,让作者直接改稿。页面有未保存修改时会每 2 分钟自动保存一次,也可以随时点击“保存草稿”立即提交:

```bash
python3 "{{skill_root}}/scripts/serve_preview.py" --manifest "<编辑 manifest 路径>"
```

`--manifest` 绑定这一篇文章;可选 `--port 0` 自动选择空闲端口,`--ready-file <未存在路径>` 新建权限为 0600 的就绪 JSON(`url/origin/pid`)。服务只监听 `127.0.0.1`,随机会话 URL 作为本机资源保管,会话 token 不写 manifest 或正文。结束服务按 Ctrl+C,已保存稿保留。`file://` 无保存服务,按钮禁用并提示从服务打开,不得冒充保存成功。

仅作者明确要求只读预览时,使用 `wrap_preview.py "<正文 HTML>"` 生成可复制静态预览。非 `minimal` 主题或找不到可靠来源映射时,说明当前编辑支持范围并交付只读预览,不冒充可编辑。默认可编辑不代表创建或同步公众号草稿授权。

9. 保存与交付人工修订:
   - 作者在服务页点击“保存草稿”,或由页面每 2 分钟自动触发保存时,同源请求经共享事务校验、快照并回填绑定的 Markdown、正文 HTML、预览和 manifest;以磁盘 `saved`、修订号及哈希为准。自动保存只提交已有未保存修改,不改变手动保存的事务边界。工具条的“添加一行”按当前光标/选区结束位置插入软换行，点击章节编号也会使用所属标题块。若来源是排版工作副本,只回填该副本,不得声称其它原稿也已保存。
   - H2 视觉序号和 H3 标题前缀序号都属于可编辑文字；选中序号即可修改或删除，保存会分别回写 H2 序号覆盖标记和 H3 标题正文，撤销/重做与自动保存继续共用同一事务。
   - 保存不清当前页撤销/重做历史,删段→保存→撤销→再次保存可形成新修订。保存期间可继续编辑,成功只标记提交时的版本,新输入仍为未保存,下一次自动或手动保存再提交。失败保留页面并可重试,未确认结果不冒充成功。关页重开不恢复 undo 历史,仅保留磁盘稿;不使用 localStorage 假保存。
   - 每轮保留 `.gzh-edits/<article_id>/rNNNN-<8hex>/` 的前后稿、manifest 和内部事务包。保存使用 manifest 锁,失败尝试恢复并留 `failed.txt`;中断锁须核实进程停止后人工处理。包是内部传输/历史兼容,现行编辑器没有导出/另存按钮。
   - 同步前核对页面当前无未保存修改,再运行 `preflight_edit.py --manifest <基线>`。磁盘预检不能证明浏览器没有新输入;仅旧兼容包按附录用 `--pending-package <路径>` 检查,不把导出/导入作为日常用户步骤。
   - 同步成功回写微信 frontmatter 后,按编辑合同用 `preflight_edit.py --manifest <基线> --refresh-metadata-from <成功同步写前源备份>` 并携带实际发送时的 `--expected-revision`、`--expected-source-sha256`、`--expected-html-sha256` 校验;加 `--apply` 才登记白名单元数据变化,保留人工 revision、刷新来源映射/哈希与绑定预览。CLI 成功 writeback 后自动调用,MCP 编排复用此命令。请求期间新修订、正文或其它元数据变化仍阻断;若草稿已创建但登记失败,保留草稿 ID 和备份,先处理冲突,不得再次 create。
   - 来源漂移、危险链接/字段、图片顺序或 H3 数量变化时停止,不覆盖；H3 序号本身可以修改或删除。保存只授权本地修订;同步公众号仍需作者另行确认,沿用 `wechat-draft-sync` 的三方比较与冲突处理,不自动合并线上修改。

默认主题完整命令:

```bash
python3 "{{skill_root}}/scripts/render_markdown.py" "<临时工作副本>" "<输出 HTML>" --theme minimal --require-semantic-anchors
```

AI 日报公众号正文完整命令:

```bash
python3 "{{skill_root}}/scripts/render_markdown.py" "<AI 日报临时工作副本>" "<输出 HTML>" --theme minimal --mode ai-daily --require-semantic-anchors
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
- `regression.py` 跑通公众号样例、压力样例、AI 日报模式、章节覆盖和长段落语义锚点边界,并确认原始日报与旧 `--target pudding` 被拒绝。
- 无人工修订时正式初排启用覆盖率门禁;已有人工修订按显式样式渲染,不得通过重排把作者取消的红色或粗体加回。
- `python3 "{{skill_root}}/scripts/release_check.py"` 完整门禁通过;`--static-only` 仅检查静态分发项,不能替代功能回归。浏览器编辑/保存另按[共享验证说明](references/editable-preview.md#独立夹具验证)运行 DOM 与 HTTP 端到端用例。
- 预览页可复制,复制区域不包含按钮、脚本或预览外壳。
- 独立编辑夹具覆盖删除、红/粗独立切换、直接保存、保存后撤销再保存、16 图顺序和 11 个 H3 块数量、H2/H3 序号编辑、来源漂移与旧包兼容;分别报告 HTTP 链路、真实文章及微信端的实际验收状态。
