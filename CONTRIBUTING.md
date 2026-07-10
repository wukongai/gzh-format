# Contributing

感谢你帮助改进 `gzh-format`。这个项目优先接受能够复现、能够验证、不会扩大权限边界的修改。

## 开始前

1. 阅读 [SKILL.md](SKILL.md)，确认改动仍属于排版、预览或校验范围。
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
- 不要增加网络请求、凭证读取、自动上传或发布行为；如果确实需要，应拆成独立的高权限工具。

## 必跑验证

```bash
python3 scripts/component_lint.py .
python3 scripts/regression.py
```

如果本机安装了 `skillhub`，再运行：

```bash
skillhub lint-skill .
skillhub doctor-skill . --profile team
```

提交说明应包含：改了什么、为什么改、用什么样例验证、是否影响现有主题或输出结构。

## 许可证

提交贡献即表示你有权提交这些内容，并同意贡献以本项目的 GNU AGPL-3.0-or-later 许可证发布。不要提交来源不明的模板、图片、字体、品牌素材或大段受版权保护的内容。

