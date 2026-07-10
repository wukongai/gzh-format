---
title: API 中转站自检样例
---

> 最近很多人都在问：有没有靠谱的 API 中转站？

![示意图](https://example.com/router.png)

## 一、为什么要自检

中转站返回 200 不代表模型真的吃到了完整 prompt。你需要同时看响应内容、usage 字段和渠道日志。

**假成功** 比报错更危险，因为它会骗过自动化流程。

## 二、三步诊断

- usage 对账
- 本地回显实验
- 同 prompt 换渠道对照

```python
print("check usage first")
```

> 渠道是易耗品，路由层才是资产。
