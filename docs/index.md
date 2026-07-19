# Kimi Adapter 文档

让 Claude Code 的 VS Code 扩展顺畅使用 Kimi 后端的本地轻量代理。

- [返回项目首页（GitHub）](https://github.com/shkyyy18/kimi-adapter)
- [KIMI 适配 VS Code 搭建手册](VSCODE_SETUP.md)

## 快速开始

```bash
git clone https://github.com/shkyyy18/kimi-adapter.git
cd kimi-adapter
python -m kimi_adapter.cli
```

默认监听 `http://127.0.0.1:18231`，将 Claude Code 的 `ANTHROPIC_BASE_URL` 指向该地址即可。
