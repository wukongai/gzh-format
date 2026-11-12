---
title: 长段落语义锚点回归
type: article
status: draft
created: 2026-07-24
updated: 2026-07-24
tags: [公众号排版, 回归测试]
related:
  - "[[gzh-format]]"
---

# 长段落语义锚点回归

## 长段落只提炼原文短语

公众号长文真正影响扫读效率的，不是字号是否再大一号，而是读者面对连续论述时能不能在几秒内抓到判断依据。排版流程需要先保留原句和事实顺序，再从已经存在的表达中选出<mark data-gzh="semantic-anchor">最关键的判断短语</mark>作为视觉锚点；如果一段同时包含原因和结论，也最多补充一个<mark data-gzh="semantic-anchor">能够独立理解的结果</mark>。这样既不会把整段染成红色，也不会让模型借着“提炼”的名义改写观点，读者仍然看到完整原文，只是扫读路径更清楚。

短段落保持原样，不自动标红。

## 与既有行内语义共存

这一段用于验证新锚点不会吞掉原有 Markdown 语义：**普通加粗仍然是普通加粗**，[可点击链接](https://example.com/semantic-anchor) 仍然保持链接，`inline_code` 继续走行内代码，<u>显式下划线</u>也继续使用原来的橙色下划线。只有没有被其它标记包裹、确实承担本段结论的<mark data-gzh="semantic-anchor">原文关键短语</mark>会变成红色加粗；账号固定关注语“学习 AI 底层能力和实操干货”仍由既有规则自动识别，不需要再套语义锚点。整段的事实、词序和标点都必须保留，renderer 只消费显式标记，不能在最终 HTML 上做随机替换。

```html
<mark data-gzh="semantic-anchor">代码里的示例标记保持代码文本</mark>
```
