# 内容模式索引

内容模式决定同一主题下的文章骨架和语义映射，不改变主题配色。主题与模式正交：先选 `theme_id`，再选 `content_mode`。

| 模式 | 标识 | 自动命中 | 规则文件 | 确定性渲染 |
|---|---|---|---|---|
| 通用长文 | `default` | 未命中其它模式 | 主题自己的 `components.md` | `minimal` 支持 |
| AI 日报公众号正文 | `ai-daily` | frontmatter `content_mode: ai-daily` / `gzh_mode: ai-daily`，或文件名以 `-AI日报-公众号正文.md` 结尾 | `modes/ai-daily/mode.md` | `minimal` 支持 |

## 选择规则

- 显式 `--mode` 优先于自动识别；显式值与 frontmatter 冲突时停止并报告。
- `ai-daily` 只接受已经写成公众号正文的独立 Markdown，不直接排原始 `YYYYMMDD-AI日报.md` 链接清单。
- 发现原始日报时，要求上游先根据已核验来源或已审核口播稿生成 `YYYYMMDD-AI日报-公众号正文.md`；`gzh-format` 不负责改写事实。
- 一篇文章只使用一个内容模式，不在中途切换。
