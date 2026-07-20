# AGENTS.md — kimi-adapter

## 项目定位

本地轻量 HTTP 代理：让 Claude Code 顺畅使用 Kimi 后端——透明转发请求，把 Anthropic 原生 `document` 附件块转换为 Kimi 网关可接受的 `text` 块；API Key 不经手。

## 技术栈

- Python ≥ 3.8；运行时仅 `pyyaml>=6.0`（可选 `pypdf`）
- 主包 `kimi_adapter/`（cli / config / adapter）；根目录 `kimi-adapter.py` 是 **LEGACY 单文件版**，保留向后兼容，不再新增功能
- 测试：pytest；lint：ruff + black（line-length 100，py38 target）
- 已知坑：`pytest.ini` 里写的是 `[tool.pytest.ini_options]` 段名（pyproject 风格），pytest 实际不生效，修正前先以命令行为准

## 常用命令

```bash
pip install -e ".[dev]"
python -m pytest -q
ruff check .
black --check .
```

## 本仓库 agent 的搜索范围与要求

- 只允许改动本仓库；LEGACY `kimi-adapter.py` 只做必要 bug 修复，新功能一律进 `kimi_adapter/` 包。
- **Claude Code 协议兼容是硬约束**：代理的核心设计是"只最小改写 `document` 块、其余原样透传"。任何改动不得破坏这一行为——不改写其他内容块、不动认证头、不缓存/记录请求体中的敏感内容。
- API Key 不经手原则不得破坏：不得新增任何把 key 写日志/写文件/转发到第三方的代码路径。
- Windows 用户是一等用户（start.bat / start.ps1）：涉及控制台输出、路径、启动脚本的改动需考虑 Windows 控制台编码（GBK）环境。

## 升级建议有效性 / 采纳规则（本仓定制）

1. 凡涉及请求/响应转换逻辑（`convert_documents` 等）的建议：必须附 Anthropic 内容块 schema 层面的证据，且同步补充 `tests/test_convert.py` 用例，否则无效。
2. 凡扩大代理改写范围（不再只是 document→text）的建议：默认**记录不做**，需用户明确批准——最小侵入是兼容性的根基。
3. 性能/缓冲类改进（legacy 版有缓冲重试逻辑、包版没有）：有效即可排期，但不得引入新的运行时依赖。
4. 文档/启动脚本/编码兼容性改进：低风险，有效即可排期做。

## 升级建议 backlog

### 1. Windows GBK 控制台中文日志编码风险

- **描述**：LEGACY `kimi-adapter.py` 通过 `print()` 输出大量中文日志（如 `kimi-adapter.py:24-25,100,295`），在非 GBK codepage 的控制台或输出重定向到 ASCII 环境时有 `UnicodeEncodeError` 风险；包版日志目前全英文、无实际暴露。README 未注明 `PYTHONIOENCODING=utf-8`，代码无编码兜底（无 `sys.stdout.reconfigure`）。
- **发现日期**：2026-07-20
- **来源任务**：agent 编码兼容性排查（AGENTS.md 建立任务核对）
- **预估价值/成本**：价值低-中（仅 legacy 版受影响，属防御性改进）；成本小（README 加一节说明，或 legacy `_log()` 加 try/except 兜底）。
- **状态**：待评审
