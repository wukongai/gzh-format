# 2026-07-11 分发与渲染评估记录

## 范围

本记录只证明本次提交的安装完整性和确定性渲染行为，不声称提高了文章传播效果或审美偏好。

## Baseline

旧分发结构把 `SKILL.md` 放在仓库根目录。使用 `npx skills add` 进行远程或本地 copy 安装时，安装结果只包含 `SKILL.md`，缺少 `scripts/`、`themes/`、`assets/` 和测试文件，因此无法运行回归。

## Candidate

候选结构把完整包放在 `skills/gzh-format/`，仓库根目录不再放 `SKILL.md`。

2026-07-11 在两个全新临时项目中执行：

```bash
npx -y skills@latest add <local-repository> --skill gzh-format --agent codex --copy --yes
npx -y skills@latest add <local-repository> --skill gzh-format --agent claude-code --copy --yes
```

两个安装结果都包含 `SKILL.md`、许可证、`scripts/`、`themes/`、`references/`、`assets/` 和 `tests/`；随后从各自安装目录运行 `python3 scripts/regression.py`，结果均为 `regression ok`。

## Held-out renderer case

`tests/evaluation/held-out-mixed.md` 不进入日常 `scripts/regression.py`，用于单独检查 YAML frontmatter、引用、混合内联语法、列表、表格、代码块、长英文和远程图片。

验收命令：

```bash
python3 scripts/render_markdown.py tests/evaluation/held-out-mixed.md <temp>/held-out.html --theme minimal
python3 scripts/validate_gzh_html.py <temp>/held-out.html
```

要求：渲染命令退出码为 0，校验为 0 ERROR，输出不包含 `private_note`。

本次执行结果：渲染退出码为 0，校验输出“完全合规”且为 0 ERROR；对产物搜索 `private_note` 无匹配。

## Negative transfer gate

`scripts/regression.py` 继续要求旧的 `--target pudding` 调用失败，防止公众号 Skill 重新扩张到非微信公众号平台；凭证读取、草稿创建、发布与群发仍由 contract 和 `SKILL.md` 明确禁止。

## Independent review

本次没有编辑者之外的独立 reviewer。该缺口必须在发布说明中保留，不得把本记录表述为下游 utility 或全面效果评测。
