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
    format-normalize.md            # 非 Markdown 输入归一化
    theme-generator.md             # 新主题生成与登记
    architecture.md                # 本文件
  themes/
    _shared/common-components.md   # 跨主题共用组件
    minimal/components.md          # 默认主题:简约
    red/components.md              # 红色
    green/components.md            # 绿色高密度主题
  scripts/
    render_markdown.py             # 默认主题确定性公众号 HTML 渲染器
    component_lint.py              # 组件库源头关
    validate_gzh_html.py           # 产物关
    wrap_preview.py                # 预览外壳
    regression.py                  # 样例回归
  assets/
    sample-article.md              # 演示输入
    theme-previews/                # 主题生成器预览输出
  docs/gallery/                    # 人工浏览主题效果
  tests/fixtures/                  # 回归夹具
    stress-markdown.md             # 压力回归:行内语法/列表/表格/引用/分隔线
```

## 职责边界

- `SKILL.md`:触发、输入输出、主题选择、校验命令、禁止项。
- `README.md`:给第一次接触本项目的用户阅读,负责产品介绍、安装、使用和常见问题;不承载 agent 执行规则。
- `LICENSE` / `THIRD_PARTY_NOTICES.md`:明确 AGPL 许可、上游作者版权和本地修改边界。
- `skill.contract.yaml`:给 skillhub 和 agent 读取的机器契约,避免复杂 skill 靠口头上下文运行。
- `references/theme-index.md`:主题名、标识、适用场景、组件库路径。
- `themes/<id>/components.md`:具体设计变量、组件 HTML、文章骨架、配方、Markdown 映射。
- `themes/_shared/common-components.md`:代码块、图片、素材占位等所有主题都可复用的基础组件。
- `scripts/`:确定性渲染、检查、预览生成和回归验证。
- `assets/`:示例输入和主题生成器预览资产。
- `tests/fixtures/`:真实或压力回归样例,用于防止 Markdown 映射和样式约束回退。

## 维护原则

- 改视觉风格,只改对应主题的 `components.md`。
- 改主题选择,只改 `theme-index.md`。
- 改通用组件,只改 `_shared/common-components.md`。
- 新增主题是加目录和登记索引,不是改厚主入口。
- 新增确定性渲染能力时,给主题加 renderer adapter,或扩展 `render_markdown.py`;不要把模板逻辑写进 `SKILL.md`。其它平台能力应拆成独立 skill,不在本入口增加 target。
- 改主题后先跑 `component_lint.py`,生成产物后再跑 `validate_gzh_html.py`。
- 改 renderer / contract / 回归用例后,必须跑 `scripts/regression.py` 和 `skillhub doctor-skill skills/gzh-format --profile team`。

## 跨主题语义契约

- 开篇引言的视觉容器已经表达引用语义,各主题不应再自动添加首尾装饰引号。
- 多行开篇引言允许换行,但 Markdown 引用中的空白行必须折叠;相邻非空行之间最多输出一次换行。
- 非开篇引用仍由各主题自行选择引号、竖线或卡片样式,不受开篇引言契约影响。
- 新增 renderer adapter 时,必须用 fixture 同时覆盖“无装饰引号”和“无双换行”。
