---
title: gzh-format 安全边界
type: guide
status: active
created: 2026-08-02
updated: 2026-10-25
tags: [公众号, 本地保存, 安全]
related:
  - "[排版入口](skills/gzh-format/SKILL.md)"
  - "[编辑与保存合同](skills/gzh-format/references/editable-preview.md)"
---

# Security policy

## Security boundary

`gzh-format` 的默认能力是本地 Markdown 解析、HTML 生成、校验、可编辑预览和作者本地修订保存。排版与校验不需要网络;直接保存只通过浏览器与 `127.0.0.1` 的同源服务通信,不访问外网或微信。它不应读取：

- 微信 AppID、AppSecret 或 access token
- 环境变量或 `~/.config/wechat-draft-sync/` 等其它工具的凭证配置
- cookie、浏览器登录态或 Keychain
- `.env`、私钥或云服务凭证
- 用户未明确指定的文章和目录

它也不应自动上传图片、创建公众号草稿、发布或群发。

保存服务只绑定启动时选择的单篇文章 manifest,校验 Host/Origin 与随机会话身份,不接受 HTTP 指定文件路径。保存前核对来源、备份并保护图序与 H3 块数量；H2/H3 序号允许作者单独修改或清空。来源漂移或非法输入拒绝覆盖。随机会话 URL 按本机资源保管,会话 token 不写 manifest 或正文。`file://` 无服务时保存禁用;本地保存不授权公众号同步。完整边界见[编辑与保存合同](skills/gzh-format/references/editable-preview.md)。

只使用排版、预览和手工复制时,用户无需配置任何公众号凭证。自动草稿属于独立 `wechat-draft-sync` 的能力;该工具应在本地检查和读取自己的 BYOK 配置,不得把真实密钥回传给 Agent 或写入本仓库。

## Reporting a vulnerability

如果你发现路径穿越、任意文件覆盖、预览页脚本注入、凭证读取、未声明网络请求或其他安全问题，请使用 GitHub 的私有漏洞报告功能联系维护者，不要先公开包含利用细节的 Issue。

报告建议包含：

- 受影响版本或 commit
- 最小复现输入
- 预期行为和实际行为
- 影响范围
- 可选的修复建议

普通排版错误、主题视觉建议和兼容性问题可以直接提交公开 Issue。
