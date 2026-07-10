# Security policy

## Security boundary

`gzh-format` 的默认能力是本地 Markdown 解析、HTML 生成、校验和预览。它不需要网络，也不应读取：

- 微信 AppSecret 或 access token
- cookie、浏览器登录态或 Keychain
- `.env`、私钥或云服务凭证
- 用户未明确指定的文章和目录

它也不应自动上传图片、创建公众号草稿、发布或群发。

## Reporting a vulnerability

如果你发现路径穿越、任意文件覆盖、预览页脚本注入、凭证读取、未声明网络请求或其他安全问题，请使用 GitHub 的私有漏洞报告功能联系维护者，不要先公开包含利用细节的 Issue。

报告建议包含：

- 受影响版本或 commit
- 最小复现输入
- 预期行为和实际行为
- 影响范围
- 可选的修复建议

普通排版错误、主题视觉建议和兼容性问题可以直接提交公开 Issue。

