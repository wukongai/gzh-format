---
title: gzh-format 发布流程
type: guide
status: active
created: 2026-08-02
updated: 2026-11-12
tags: [公众号, 分发, 发布验证]
related:
  - "[产品说明](README.md)"
  - "[贡献说明](CONTRIBUTING.md)"
  - "[编辑保存验证](skills/gzh-format/references/editable-preview.md#独立夹具验证)"
---

# Releasing gzh-format

## Single source of truth

发布前的唯一运行时源头是 Content-factory 中的 `skills/gzh-format/`。公开仓库在同名的 `skills/gzh-format/` 保存可安装包；根目录只维护 README、贡献说明、发布说明、许可证和 CI。

同步时必须使用可审计的确定性复制或导出流程，不得把 Skill 展平到仓库根目录。根目录出现 `SKILL.md` 会让部分安装器把它识别成单文件 Skill，从而遗漏脚本与主题。

独立仓库使用自己的版本号；Content-factory 同期用主仓版本记录分发契约变化。

## Pre-release checks

从独立仓库根目录运行：

```bash
python3 skills/gzh-format/scripts/release_check.py
```

命令说明：

- `release_check.py`：检查安装包完整性、相对链接、用户绝对路径、secret-like 内容和 Python 语法,再调用 `regression.py` 运行完整排版与共享保存 Python/HTTP 夹具。测试不调用外网或微信;本机 HTTP 用例需要 loopback 端口可用。
- `--static-only`：只做静态分发检查,不能据此报告完整回归通过。

公开 CI 同时运行六组 Python 平台检查和一个 Ubuntu 浏览器任务（43 项 DOM/HTTP 用例），覆盖手机宽度、编辑状态与直接保存。

本地浏览器直接保存另在 Skill 目录运行:

```bash
node --test tests/test_editor_dom.cjs tests/test_editable_e2e.cjs
```

`--test` 运行 DOM 与真实本机 HTTP 端到端用例,执行命令的 Node 须能解析 `playwright`,并有可用 Chromium/Chrome。已有依赖可用 `NODE_PATH="<已有 node_modules 目录>"` 接入,浏览器可用 `GZH_TEST_BROWSER="<已有浏览器可执行文件>"` 指定。当前本机 SkillHub 没有旧 `lint-skill` / `doctor-skill` 子命令,不将它们作为发布通过门禁;可选项目入口环境巡检不能替代上述验证。夹具、真实文章和微信端的证据分别记录,见[共享验证说明](skills/gzh-format/references/editable-preview.md#独立夹具验证)。

随后确认：

- 根目录包含 `README.md`、`LICENSE`、`THIRD_PARTY_NOTICES.md`、`CHANGELOG.md`。
- `skills/gzh-format/` 包含自己的 `SKILL.md`、许可证、脚本、主题、样例和测试。
- 仓库根目录没有 `SKILL.md`，避免安装器误判为单文件 Skill。
- README 的仓库地址、版本、主题支持范围与实际一致。
- 没有用户绝对路径、真实文章、凭证、cookie、token、`.env` 或缓存目录。
- `minimal` 才是确定性 renderer；除非 adapter 已实现并有 fixture，不宣传 `red/green` 一键脚本渲染。
- GitHub Actions 的 Ubuntu、macOS、Windows × Python 3.9/3.14 矩阵全部通过后，才能扩大操作系统兼容承诺。

## Clean install smoke test

用一次性目录分别模拟 Codex 和 Claude Code 安装：

```bash
npx skills add <仓库路径或 URL> --skill gzh-format --agent codex --copy --yes
npx skills add <仓库路径或 URL> --skill gzh-format --agent claude-code --copy --yes
```

每个安装目录至少检查：

```bash
test -f <安装目录>/SKILL.md
test -f <安装目录>/LICENSE
test -f <安装目录>/scripts/regression.py
test -f <安装目录>/scripts/serve_preview.py
test -f <安装目录>/assets/editor.js
test -f <安装目录>/themes/minimal/components.md
python3 <安装目录>/scripts/release_check.py
```

`test -f` 用于确认关键文件实际存在；安装器显示“success”但缺少 `scripts/` 时仍视为失败。

推送后还要分别用 GitHub 和 Gitee URL 重做一次远程安装。只有两个远程都能安装完整包并跑通回归，发布才算完成。

## Export

从 Content-factory 的 `skills/gzh-format/` 同步到公开仓库的同名目录，保留公开仓库根文档和 `.github/`。同步后先查看 `git diff --stat` 和 `git diff --check`，再执行上面的离线检查与干净安装回归。

不要再使用把 `skills/gzh-format/` 导出为仓库根目录的 `git subtree split` 结果直接覆盖主分支；那种结构会破坏当前通用安装器的完整复制行为。
