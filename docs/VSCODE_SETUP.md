# KIMI 适配 VS Code 搭建手册

本手册说明如何将 **Claude Code for VS Code** 扩展的后端切换到 **Kimi**，并使用 Kimi Adapter 解决附件兼容性问题。

## 前置条件

1. 安装 Claude Code for VS Code 扩展（`anthropic.claude-code`）
2. 开通 Kimi Code 权益并创建 API Key（`sk-` 开头）：https://www.kimi.com/code
3. 安装 Kimi Adapter：

```bash
pip install git+https://github.com/njshk/kimi-adapter.git
kimi-adapter
```

## 配置后端地址

运行 `设置Kimi密钥.py`（或手动修改配置），把 `ANTHROPIC_BASE_URL` 指向 Adapter：

```
ANTHROPIC_BASE_URL = http://127.0.0.1:18231
```

## 启动方式

- 手动：`kimi-adapter`
- 随 VS Code 启动：将项目里的 `.vscode/tasks.json` 示例复制到工作区

## 注意事项

- Adapter 只转换文本类附件；PDF/图片仍可能报错
- Adapter 不运行时，所有请求会失败，请保持 Adapter 在后台运行
- 关闭扩展自动更新，避免换肤/配置被覆盖

完整换肤步骤见桌面主手册。
