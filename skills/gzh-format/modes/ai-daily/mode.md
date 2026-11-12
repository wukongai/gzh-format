---
title: AI 日报公众号模式
type: reference
status: active
created: 2026-08-02
updated: 2026-10-25
tags: [公众号, AI日报, 预览保存]
related:
  - "[排版入口](../../SKILL.md)"
  - "[编辑保存说明](../../references/editable-preview.md)"
  - "[正文模板](template.md)"
---

# AI 日报公众号模式

把已经写好的 AI 日报公众号正文按 `minimal` 主题排成微信编辑器兼容 HTML。该模式固化 2026-07-13 实际发布稿的结构，只负责排版，不抓来源、不写正文、不创建草稿。

## 输入门禁

- 优先输入 `YYYYMMDD-AI日报-公众号正文.md`。
- frontmatter 使用 `content_mode: ai-daily`，兼容旧字段 `gzh_mode: ai-daily`；主题固定 `paiban_template: minimal` 或 CLI `--theme minimal`。
- 禁止直接输入 `YYYYMMDD-AI日报.md`。原始日报的链接目录、`<audio>`、转写 callout、Pudding 字段不是公众号正文。
- 正文不得包含本地绝对路径、Obsidian 音频嵌入、HTML `<audio>` 或转写 callout。
- 微信公众号正文必须来自已核验来源或已审核口播稿；本模式不补事实、不扩写低置信来源。

## 固定骨架

1. frontmatter：`title`、`date`、`author`、`digest`、`niche`、`content_mode: ai-daily`、`paiban_template: minimal`。
2. 音频位：正文最顶部保留且最多保留 1 个 `【请在此处插入本期 MP3 音频】`，渲染为正文样式的空白段落（无框、无提示文字），用户在公众号后台该位置直接插入原生音频；不得输出网络 `<audio>` 或本地 MP3 路径。
3. 开篇：2 段，第一段交代当天变化，第二段给出贯穿全文的主线；不渲染 hero 卡，标题和封面由公众号草稿层负责；正文顶部（音频位与开篇区域）不放任何配图，插图只出现在正文章节内。
4. 主体：4–6 个 H2 章节。H2 按 `01`、`02`、`03` 编号，章节标题用“主题：判断”或短判断句；每章 2–4 个自然段。
5. 收束：放在最后一个正文章节内，完成“当日总判断 → 企业/个人意义”；不追加通用 hero、作者卡或三连 CTA。
6. 来源：最后固定 `## 今日参考资料`，说明区由渲染器固定渲染为一行「以下链接仅作信息来源和延伸阅读，整理来自青影星球，版权归原作者及原发布账号所有。」（归属与版权合并为一行，不再分两行；源文里旧的两行写法会被忽略），然后用编号列表放标题和 `查看原文` 链接。渲染时降级为 11px 低权重来源区，不计入章节编号。
7. 文末：参考资料区之后固定渲染一个正文样式的空段落，保证用户在公众号后台回车时是干净新段落，可直接插入页尾模板。

使用 [template.md](template.md) 新建正文骨架。

## 视觉映射

- 使用 `minimal` 的全局容器、正文段落和编号章节标题。
- 开篇不加 hero 卡，保留连续阅读感。
- 音频位渲染为空白段落，不加虚线框、底色或提示文字，方便微信后台直接插入原生音频。
- `今日参考资料` 使用顶部细线、13px 小标题、11px 归属句/声明与条目；链接颜色降为中性灰，不抢正文权重。
- 文末固定一个正文样式空段落，不加额外卡片或 CTA。
- 正文不主动加下划线、高亮框或额外卡片；只保留源文显式加粗等语义。

## 命令

```bash
python3 scripts/render_markdown.py "<实际公众号正文工作副本.md>" "<输出.html>" --theme minimal --mode ai-daily
python3 scripts/validate_gzh_html.py "<输出.html>"
python3 scripts/wrap_preview.py "<输出.html>" --editable --source-md "<实际公众号正文工作副本.md>"
python3 scripts/serve_preview.py --manifest "<输出.gzh-edit-manifest.json>"
```

在 Skill 目录执行;`--theme minimal` 与 `--mode ai-daily` 选择主题和正文模式,校验通过后默认用 `--editable` 建立编辑基线,`--source-md` 绑定实际渲染及保存目标。serve 的 `--manifest` 指定正文同目录同名前缀基线,打开其首行 URL 直接改稿并“保存草稿”;保存后仍可撤销/重做,不自动同步微信。只读例外、来源冲突和保护范围按[共享说明](../../references/editable-preview.md#打开能直接保存的预览)处理。

## 验收

- 正文章节数为 4–6，`今日参考资料` 不出现大号章节编号。
- HTML 中不含 `<audio`、`.mp3` 本地路径、`![[`、`视频转写`、`pudding_id` 或 `pudding_url`。
- 音频占位渲染为空白段落，HTML 中不出现“微信原生音频位”等提示文字。
- 来源区保留全部标题与链接，且使用低权重样式；说明区为固定单行「以下链接仅作信息来源和延伸阅读，整理来自青影星球，版权归原作者及原发布账号所有。」。
- 文末有且仅有正文样式空段落作为收尾。
- `validate_gzh_html.py` 为 0 ERROR;默认可可靠映射的正文交付可编辑、可保存服务 URL,保存后仍能撤销/重做,复制区域只含正文。
