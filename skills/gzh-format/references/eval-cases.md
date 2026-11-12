---
title: gzh-format 触发、主题与编辑保存回归用例
type: reference
status: active
created: 2026-07-07
updated: 2026-10-25
tags: [公众号, 回归, 预览保存]
related:
  - "[排版入口](../SKILL.md)"
  - "[主题路由](theme-index.md)"
  - "[编辑保存验证](editable-preview.md#独立夹具验证)"
---

# 触发与主题选择 · 回归用例

维护本 skill（改 description、加主题、调路由）后用这组用例核对，确保该触发时触发、不该触发时不触发、主题推荐合理。

## 正例（应触发 gzh-format）

- "帮我把这篇 Markdown 做成公众号排版"
- "微信公众号文章排版"
- "gzh，这篇用 XX 主题"（XX 为 theme-index 中已注册主题）
- "把下面这篇文章转成能直接粘进公众号编辑器的 HTML"
- "这篇文章帮我排个版，发公众号用"
- "给公众号排版生成一套新主题 / 自定义风格"（→ 自定义主题生成流程）
- "按这张参考图帮我做一套公众号排版组件库"（→ 自定义主题生成流程）
- "在公众号预览里改这段字、取消红色并保存草稿"（→ 共享本机编辑保存流程）
- "撤销刚才已保存的删段,再保存"（→ 保留当前页历史并保存新修订）

## 反例（不应触发，应转其它能力）

- "帮我做一个网页落地页" → 前端/web skill
- "把内容做成 PPT" → PPT skill
- "帮我排版这个 Word 文档" → 排版对象不是公众号
- "写一篇公众号文章" → 这是写作，不是排版（先有 Markdown 才用本 skill）

## 主题选择行为（默认简约）

- 用户指定了 theme-index 中已注册的主题 → 直接执行不提问
- 用户没有指定主题 → 直接使用「简约」(`minimal`),不按题材再弹主题选择
- 用户要看可选主题 → 展示 [theme-index.md](theme-index.md) 的已注册主题与适用场景,按其明确选择执行
- 用户只说"公众号排版这篇 md / 直接排 / 一键 / 不用问" → 默认 minimal;来源可可靠映射时交付可编辑、可保存服务 URL
- 用户选定主题后 → 在该主题内部按"文章类型 → 组件组合配方"匹配组件
- theme-index 为空（无已注册主题）→ 不排版，告知用户先添加主题风格，不要凭记忆编造主题

## 关键行为核对（用 assets/sample-article.md + tests/fixtures/stress-markdown.md 跑一遍）

- [ ] 未指定主题时直接用 minimal,不要求作者另说“我要编辑”或再选主题
- [ ] 解析结构后判定了文章类型，并按主题库「文章类型 → 组件组合配方」表选组件组合（不是逐段随机选）
- [ ] 点缀组件种类不超过配方表规定的上限
- [ ] 目录/导航组件位置符合主题骨架（绿色：toc-scroll 紧跟封面之下，在引言和前言之前）
- [ ] 正文引号生成时即为全角弯引号，无需事后替换
- [ ] 代码块走代码块组件，不塞进段落
- [ ] 代码块不会横向撑破:每行代码带 `overflow-wrap:anywhere;word-break:break-word`
- [ ] 图片用图片组件、GIF 加动图角标
- [ ] 正文半角标点被改成中文全角（代码块内不动）
- [ ] 开头引言卡署名按文章作者/主题定，不固定"甲木"
- [ ] 尾部签名区默认用 `{{作者名}}` 占位（不写死人名）；用户给了署名才填入，原文已有签名则沿用原文
- [ ] 原文已有签名段时合并进唯一签名区，不重复
- [ ] 强调/小标题用小标签或左竖条，无虚线框
- [ ] 代码块紧凑：每行一个 `<p style="margin:0">`，无 `white-space:pre`，无大段空白
- [ ] `【插入…】` 类待补占位用 2c 居中板块，不是左对齐提示块
- [ ] 骨架按所选主题库的"完整文章模板骨架"装配，不套用其它主题骨架
- [ ] 生成后跑 scripts/validate_gzh_html.py，ERROR 与半角 WARNING 清零
- [ ] `tests/fixtures/stress-markdown.md` 中的 `==高亮==`、`<u>`、`++下划线++`、`~~删除~~`、有序列表、表格、非开头引用和 `---` 跳过规则都没有回退
- [ ] `tests/fixtures/stress-markdown.md` 中的 Markdown/YAML 长行代码块在公众号预览里自动换行,不需要横向拖动
- [ ] `tests/fixtures/semantic-highlights-markdown.md` 中长普通正文只输出 1-2 个 `#DC2626` 红色加粗锚点,标记本身不进入 HTML,段落纯文本与原文一致
- [ ] 短段落、每段 3 个锚点、全文密度超限、标题误用、普通加粗/链接嵌套均明确拒绝;代码块里的同名标记保持代码文本
- [ ] 固定关注语“学习 AI 底层能力和实操干货”继续自动红色加粗,不要求也不允许重复套语义标记
- [ ] `python3 scripts/release_check.py` 完整静态分发与 Python/HTTP 回归通过;`--static-only` 不冒充功能验证

## 默认编辑与保存核对

- [ ] minimal 且源文可确定性映射时执行 `wrap_preview.py --editable --source-md` 后接 `serve_preview.py --manifest`,交付服务 URL;只读例外和来源冲突按[共享合同](editable-preview.md#打开能直接保存的预览)处理
- [ ] 页面只有“保存草稿”主保存动作,真实备份回填 MD/HTML/manifest/预览,无导出或另存步骤;file 协议页禁用保存
- [ ] 保存后仍可撤销/重做并再次保存;在途新输入仍未保存,失败保留页面可重试,未确认结果不作成功
- [ ] 红色与粗体独立,显式 Markdown 列表项可改;代码、表格、自动问题/示例组、双链和固定页尾只读,图序与 H3 数量受保护,H2/H3 序号可编辑
- [ ] 来源漂移停止覆盖;人工修订不重新补红,同步前确认页面无未保存修改并执行 saved 预检,本地保存不授权微信写入
- [ ] 浏览器用例 `node --test tests/test_editor_dom.cjs tests/test_editable_e2e.cjs` 通过;环境要求与真实文章/微信未验证边界分别记录,不以静态检查替代

## 自定义主题生成行为

- 用户说"生成新主题"但只给一句风格描述 → 一次性问全偏好字段（不逐字段追问），空缺项按 theme-generator.md 规则自动补全
- 用户上传参考图 → 先 Read 提取视觉特征，只做风格转译，不复刻图中文字/Logo/构图
- 生成的区块库 HTML 保存到 `assets/theme-previews/{theme-id}.html`，全部区块在一页内连续排布，用户**整页一次浏览**确认风格（不逐块展示、不逐块确认），再转标准主题库
- 转换 `themes/{theme-id}/components.md` 时：补 `<span leaf="">`、去掉预览用 `id`、补齐五章节（变量表/组件/骨架/配方表/映射表）
- 新主题登记进 theme-index.md 且 `component_lint.py` 0 ERROR 后才算交付；之后"列全部主题让用户选"必须包含它
- 主题 ID 与已有主题冲突 → 提示换名或确认覆盖，不静默覆盖

## 格式兼容用例

- 给 `.docx` → 先跑 `scripts/extract_docx.py` 转 md，再结构确认，不直接读二进制
- 给 `.pdf` → Read 分页读取，删页眉页脚页码、合并硬断行，图位留居中占位
- 给无标记 `.txt`（含"一、二、"式标题）→ 正确推断为 `##`，结构确认后再排
- 给完全无标题的纯文本 + "直接排" → 全自动：语义分章 + 自拟标题 + 默认 minimal，交付附决策说明
- 给 `.doc` 老格式 → 提示另存为 .docx，不硬解析

## 维护 · 可验证循环

改了组件库或 SKILL 后，按这个闭环验证，确保不引入排版反模式（大空白、左对齐占位、正文虚线框、平台禁用项）：

1. **改** 组件库 / SKILL / 脚本
2. **源头关**：`python3 scripts/component_lint.py .`
   扫所有组件库的 ```html 块，检测 `white-space:pre`（大空白）、四周虚线框 `border:…dashed`（正文，居中占位块豁免）、平台禁用项（div/class/id/style/grid/position/var/@media）。须 **0 ERROR**。
3. **生成** 用改后的 skill 排版 `assets/sample-article.md`、`tests/fixtures/stress-markdown.md` 和 `tests/fixtures/semantic-highlights-markdown.md`（或真实文章）
4. **产物关**：`python3 scripts/validate_gzh_html.py <产物.html>`
   检测禁用标签、`<span leaf>` 包裹、半角标点。须 **0 ERROR、半角 0 WARN**。
5. **回归关**：`python3 scripts/regression.py`
   同时跑普通样例和压力样例,确保章节标题、行内语法、列表、表格、引用、分隔线策略不回退。
6. **分发与完整回归关**：`python3 scripts/release_check.py`
   检查包完整性、链接、安全静态项、语法和完整 Python/HTTP 回归;`--static-only` 仅用于静态核对。修改浏览器编辑或保存时,另运行上节的 DOM 与 HTTP 端到端用例。
7. 任一关不过 → 回第 1 步，直到所有关口全绿。

脚本分工：`component_lint` 管「组件库源头不含反模式」，`validate_gzh_html` 管「最终产物合规」，`regression.py` 管「已承诺映射与共享保存不回退」，`release_check.py` 管「静态分发与完整 Python 回归」。当前本机 SkillHub 没有旧 `lint-skill` / `doctor-skill`,可选入口环境巡检不作为本 Skill 通过门禁。
