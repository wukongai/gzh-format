---
title: 留出集混合语法
private_note: 不应进入正文
---

# 留出集文章标题

> 这是一段用于评估的开篇引用。

## 一个没有出现在发布样例中的章节

普通段落包含 **加粗**、==高亮==、[外部链接](https://example.com) 与 `inline_code()`。

### 混合清单

1. 第一项包含中文标点。
2. 第二项包含一段很长的英文标识：`agent_skill_catalog_installation_regression_should_wrap_without_overflow`。

| 检查项 | 预期 |
|---|---|
| YAML frontmatter | 不进入正文 |
| 公众号外层 | 只有顶层 section |

```python
def held_out_case() -> str:
    return "wechat-compatible"
```

![远程图片](https://example.com/held-out.png)
