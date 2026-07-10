# 布丁 H5 预览目标

`pudding` target 用于把同一篇 Obsidian/Markdown 长文渲染成更适合布丁 H5 阅读的预览正文片段。它复用 `gzh-format` 的语义判断,但不复用微信公众号编辑器的兼容写法。

重要:当前布丁后台的 `content` 是可编辑正文,应保存 Markdown,不要保存渲染后的 HTML。公众号 HTML、布丁 H5 预览 HTML 和布丁后台 Markdown 是三种不同产物。

## 设计边界

- 输出 H5 友好标签: `<article>`、`<h2>`、`<h3>`、`<h4>`、`<p>`、`<strong>`、`<blockquote>`、`<ul>`、`<li>`、`<figure>`、`<table>`、`<pre>`、`<code>`。
- 布丁标题优先贴近 Markdown 原生渲染效果:不要额外加章节序号、标题卡片、分隔线或公众号风格装饰。用轻量内联样式约束字号和间距即可。
- 样式保持轻量内联,避免依赖布丁前端新增 CSS 才能读。
- 不输出 `span leaf`、微信复制兼容壳、复制按钮、脚本、`html/head/body`。
- 不强行使用公众号的边框、灰底、图片框;布丁本身是 H5 页面,重点是移动端阅读节奏、图片展示和标题层级。
- 不直接调用布丁后台 API;后台同步动作交给 `pudding sync`。
- 不把 `<article>`、`<p style>`、`<span style>` 等渲染 HTML 写进布丁后台 `content`,否则编辑器会显示源码,也会破坏后续人工编辑。

## Markdown 映射原则

- `##` 映射为接近 Markdown 原生二级标题的 `<h2>`:不自动加 `01/02/03`,但必须保留原文自带的 `一、二、三` 等标题序号。
- `###` 映射为普通小节 `<h3>`。
- `第一，...`、`第一层是...` 这类短句映射为微标题 `<h4>`。
- `比如...`、`新增...`、`运行...` 等短动作句映射为轻列表,避免一连串普通段落显得散。
- 图片使用无外框大图展示,保留圆角和轻阴影。
- 代码块使用深色 `<pre><code>`,但默认必须自动换行:保留原始换行和缩进,长行用 `white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word` 折行,避免移动端横向拖动。
- 表格可以使用横向滚动容器,避免移动端挤压。

## 后台同步规则

当前 `pudding sync` 读取 Markdown 文件正文作为 `content`。要同步布丁后台可编辑正文时:

1. 直接对源 Markdown 运行 `pudding sync --force --type text` dry-run。
2. 确认 dry-run 显示 `case_id` 为目标草稿,且 `content` 预览仍是 Markdown 正文。
3. 用户确认后再运行 `pudding sync --apply --force --type text`。
4. `pudding sync` 负责把正文图片复制到布丁 OSS 并替换 URL。

不要把微信公众号 target 的 HTML 直接同步到布丁。微信版本为编辑器兼容而写,包含 `span leaf` 等平台细节,不适合作为布丁内容格式。

也不要把 `pudding` target 的 HTML 通过临时 Markdown 同步到当前布丁后台 `content`。`pudding` target 只用于:

- 本地浏览器预览布丁 H5 视觉效果。
- 未来布丁如果新增独立 `htmlContent`/渲染缓存字段时,作为该字段的输入。
- 和布丁前端讨论 Markdown 渲染样式时,提供组件参考。
