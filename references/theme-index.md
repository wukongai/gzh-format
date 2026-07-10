# 主题索引与选择决策表

本表是 `gzh-format` 的主题路由单一来源。主 `SKILL.md` 只读本表决定加载哪套主题,具体排版规则在对应 `themes/<theme-id>/components.md`。

## 已注册主题

| 主题 | 标识 | 状态 | 主色 | 适用场景 | 组件库文件 | 正文强调规则 |
|------|------|------|------|---------|-----------|-------------|
| 简约 | `minimal` | 默认 | `#1e1f23` 墨黑,配橙 `#ed7b2f` | 深度评测、案例复盘、系统性说明、技术风险排查;适合本账号当前长文风格 | `themes/minimal/components.md` | 不主动加关键词下划线;只保留源文显式 `<u>` / `++...++` |
| 红色 | `red` | 内置 | `#DC2626` 正红 | 深度分析、观点、力量感话题;经典编辑风,红色克制点睛 | `themes/red/components.md` | `border-bottom:2px solid #FECACA;font-weight:600;` |
| 绿色 | `green` | 内置 | `#059669` emerald | 教程、测评、清单、工具盘点;卡片丰富、信息密度高 | `themes/green/components.md` | `border-bottom:2px solid #A7F3D0;font-weight:600;` |

## 默认选择

- 用户没有指定主题时,直接使用「简约」(`minimal`)。
- 用户说“默认样式 / 同步公众号前先排版 / 公众号排版”时,仍使用「简约」。
- 用户指定中文名或标识时,按上表匹配。
- 用户要看可选主题时,展示上表的主题名、标识和适用场景。
- 一篇文章只用一套主题;不要跨主题混用组件。

## 新主题登记流程

1. 新建 `themes/<theme-id>/components.md`。
2. 组件库必须包含:设计变量、组件 HTML、完整文章模板骨架、文章类型配方表、Markdown 映射规则。
3. 在上表登记一行。
4. 运行:

```bash
python3 scripts/component_lint.py .
```

5. 用一篇真实 Markdown 生成 HTML,再运行 `scripts/validate_gzh_html.py`。
