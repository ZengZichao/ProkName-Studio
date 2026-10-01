# Security Policy / 安全策略

[English](SECURITY.md) | [中文](SECURITY.zh.md)

## Supported versions / 支持的版本

| Version | Supported / 是否支持 |
|---------|----------------------|
| latest release（最新发布版） | ✅ |
| `main` | ✅ |
| older releases（旧版本） | ❌ |

## Reporting a vulnerability / 报告漏洞

Please use GitHub's **private vulnerability reporting** (Security → Report a
vulnerability) instead of a public issue, so that a fix can land before the
details are disclosed.

请使用 GitHub 的**私密漏洞报告**（Security → Report a vulnerability），
不要直接开公开 Issue，以便在细节公开之前完成修复。

### Scope / 范围

This is a local-only desktop application. In scope: the bundled app and its
installer artifacts, the packaged data files, and dependency vulnerabilities
declared in `pyproject.toml` / `requirements.txt`.

这是一个纯本地桌面应用。打包产物与安装方式、随包分发的数据文件、
`pyproject.toml` / `requirements.txt` 声明的依赖漏洞均在范围内。

### Response time / 响应时间

Solo-maintained project: expect an initial reply within about two weeks.

个人维护的项目：预计两周内给出初步回复。
