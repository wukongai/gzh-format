---
title: gzh-format 贡献说明
type: guide
status: active
created: 2026-08-02
updated: 2026-10-25
tags: [公众号, 贡献, 验证]
related:
  - "[排版入口](SKILL.md)"
  - "[发布流程](RELEASING.md)"
  - "[编辑与保存合同](references/editable-preview.md)"
---

# Contributing

感谢你帮助改进 `gzh-format`。这个项目优先接受能够复现、能够验证、不会扩大权限边界的修改。

## 开始前

1. 阅读 [SKILL.md](SKILL.md)，确认改动仍属于排版、预览、作者本地修订保存或校验范围。
2. 阅读 [skill.contract.yaml](skill.contract.yaml)，不要绕过停止点和禁止动作。
3. 新功能先说明输入、输出、失败方式和验证用例。
4. 不要提交文章隐私数据、真实凭证、cookie、token 或 `.env` 文件。

## 修改主题

- 只修改对应的 `themes/<theme-id>/components.md`。
- 共用组件修改 `themes/_shared/common-components.md`。
- 新增主题时，同时登记到 `references/theme-index.md`。
- 如果希望主题支持确定性 CLI 渲染，请新增 renderer adapter 和对应 fixture，不要只修改 `SKILL.md` 承诺能力。

## 修改脚本

- 优先保持 Python 标准库依赖。
- 同样输入应得到同样输出。
- 错误必须以非零退出码暴露，不能静默跳过。
- 本机直接保存只使用绑定单篇文章的 `127.0.0.1` 同源服务;不要扩展到外部网络、任意文件写入、凭证读取、自动上传或发布。外部高权限能力交给独立工具,保存边界见[共享合同](references/editable-preview.md)。

## 必跑验证

```bash
python3 skills/gzh-format/scripts/component_lint.py skills/gzh-format
python3 skills/gzh-format/scripts/release_check.py
```

第一条检查组件源头,第二条运行静态分发检查和完整 Python/HTTP 回归。`--static-only` 仅供静态核对,不代表功能测试通过。修改浏览器编辑或保存行为时,在 Skill 目录另跑:

```bash
node --test tests/test_editor_dom.cjs tests/test_editable_e2e.cjs
```

`--test` 覆盖 DOM 和真实本机 HTTP 保存链路。当前 Node 须能解析 `playwright`,且有可用 Chromium/Chrome;已有依赖可用 `NODE_PATH="<已有 node_modules 目录>"` 接入,已有浏览器可用 `GZH_TEST_BROWSER="<浏览器可执行文件>"` 指定,详见[验证说明](references/editable-preview.md#独立夹具验证)。当前本机 SkillHub 不提供旧 `lint-skill` / `doctor-skill`;可选入口环境巡检不作为本 Skill 通过门禁。

提交说明应包含：改了什么、为什么改、用什么样例验证、是否影响现有主题或输出结构。

## 许可证

提交贡献即表示你有权提交这些内容，并同意贡献以本项目的 GNU AGPL-3.0-or-later 许可证发布。不要提交来源不明的模板、图片、字体、品牌素材或大段受版权保护的内容。
