# Kimi Adapter for Claude Code

让 [Claude Code](https://claude.ai/code) 的 VS Code 扩展顺畅使用 **Kimi** 后端的本地轻量代理。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 痛点

Claude Code 扩展会把代码/文本附件以 Anthropic 原生的 `document` 内容块发送，但 Kimi 的 Anthropic 兼容网关目前不支持该类型，直接发附件会报错：

```
API Error: 400 Invalid request Error
```

**Kimi Adapter** 跑在本地，把所有请求透明转发到 Kimi，同时把 `document` 块自动转换成 Kimi 能处理的 `text` 块，**不接触你的 API Key**。

## 特性

- 🔒 **Key 不经手**：请求头原样透传，Adapter 不读取、不存储 Kimi API Key
- 📎 **附件自动转换**：代码、Markdown、文本类附件一键转 `text` 块
- 📄 **PDF 支持（可选）**：安装 `pypdf` 后，可提取 PDF 文本内容
- 🖥️ **VS Code 随启随停**：提供任务配置，打开 VS Code 自动启动，关闭后自动退出
- ⚙️ **零依赖/轻依赖**：单文件 Python 脚本，也可作为 pip 包安装
- 🐳 **Docker 可选**：提供容器化运行方式
- 🧪 **带基础测试**：核心转换逻辑已覆盖

## 快速开始

### 方式一：直接运行脚本（最简单）

```bash
git clone https://github.com/njshk/kimi-adapter.git
cd kimi-adapter
python kimi_adapter.py
```

默认监听 `http://127.0.0.1:18231`。

### 方式二：pip 安装

```bash
pip install -e .
kimi-adapter
```

如需 PDF 附件支持：

```bash
pip install -e ".[pdf]"
```

### 方式三：Docker

```bash
docker build -t kimi-adapter .
docker run -p 18231:18231 kimi-adapter
```

## 与 Claude Code 配合使用

1. 按 [KIMI 适配 VS Code 搭建手册](docs/VSCODE_SETUP.md) 配置好 Claude Code 扩展的后端地址；
2. 把 `ANTHROPIC_BASE_URL` 从 `https://api.kimi.com/coding/` 改为：

```
http://127.0.0.1:18231
```

3. 打开 VS Code，附件即可正常使用。

## 配置

创建 `config.yaml`：

```yaml
listen_host: "127.0.0.1"
listen_port: 18231
upstream_host: "api.kimi.com"
upstream_prefix: "/coding"
vscode_watchdog: true
log_level: "INFO"
```

启动时自动读取：

```bash
kimi-adapter --config config.yaml
```

## 开发

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## 限制

- 目前支持 `source.type=text` 的附件转换和 `source.type=base64` 的 PDF 文本提取（需安装 `pypdf`）
- 图片等其他 base64 二进制附件无法转换
- Adapter 不运行时，指向它的请求会失败，请确保 Adapter 已启动

## 协议

[MIT](LICENSE)
