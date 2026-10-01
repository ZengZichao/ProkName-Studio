# 安全策略 / Security Policy

[English](SECURITY.md) | [中文](SECURITY.zh.md)

## 支持的版本 / Supported versions

| 版本 | 是否支持 |
|------|----------|
| 最新发布版（latest release） | ✅ |
| `main` | ✅ |
| 旧版本 | ❌ |

## 报告漏洞 / Reporting a vulnerability

请使用 GitHub 的**私密漏洞报告**（Security → Report a vulnerability），
不要直接开公开 Issue，以便在细节公开之前完成修复。

Please use GitHub's **private vulnerability reporting** (Security → Report a
vulnerability) instead of a public issue, so that a fix can land before the
details are disclosed.

### 范围 / Scope

这是一个纯本地桌面应用。打包产物与安装方式、随包分发的数据文件、
`pyproject.toml` / `requirements.txt` 声明的依赖漏洞均在范围内。

This is a local-only desktop application. In scope: the bundled app and its
installer artifacts, the packaged data files, and dependency vulnerabilities
declared in `pyproject.toml` / `requirements.txt`.

### 响应时间 / Response time

个人维护的项目：预计两周内给出初步回复。

Solo-maintained project: expect an initial reply within about two weeks.
