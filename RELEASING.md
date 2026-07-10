# Releasing gzh-format

## Single source of truth

发布前的唯一源头是 Content-factory 中的 `skills/gzh-format/`。公开仓库不得手工维护另一份长期副本；应通过 `git subtree split` 或等价的确定性导出方式，把该目录发布为独立仓库根。

独立仓库使用自己的版本号，从 `v0.1.0` 开始；Content-factory 同期用主仓版本记录分发契约变化。

## Pre-release checks

在 `skills/gzh-format/` 目录运行：

```bash
python3 scripts/component_lint.py .
python3 scripts/regression.py
skillhub lint-skill .
skillhub doctor-skill . --profile commercial
```

命令说明：

- `component_lint.py`：检查主题组件源头是否包含微信不兼容结构。
- `regression.py`：渲染普通样例和压力样例，并检查预览链路。
- `lint-skill`：验证 Agent Skill 基础结构。
- `doctor-skill --profile commercial`：按对外发布严格度检查边界、安全与工程化。

随后检查：

- 根目录包含 `README.md`、`LICENSE`、`THIRD_PARTY_NOTICES.md`、`CHANGELOG.md`。
- README 的仓库地址、版本、主题支持范围与实际一致。
- 没有用户绝对路径、真实文章、凭证、cookie、token、`.env` 或缓存目录。
- `minimal` 才是确定性 renderer；除非 adapter 已实现并有 fixture，不宣传 `red/green` 一键脚本渲染。

## Export

从 Content-factory 仓库根运行以下命令生成只包含该 Skill 历史的发布分支：

```bash
git subtree split \
  --prefix=skills/gzh-format \
  -b codex/gzh-format-v0.1.0
```

参数说明：

- `--prefix=skills/gzh-format`：只抽取这个目录。
- `-b codex/gzh-format-v0.1.0`：生成本地发布分支，不会自动推送。

在推送或创建公开仓库前，先把该分支检出到一次性目录，按 README 做一遍安装、首次使用和回归验证。只有干净环境通过后，才创建 tag 或公开发布。

