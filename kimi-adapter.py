# -*- coding: utf-8 -*-
# ⚠️  LEGACY SINGLE-FILE VERSION
# 本项目已重构为可 pip 安装的包（kimi_adapter/）。
# 新推荐用法：
#   pip install -e .
#   kimi-adapter
# 或：
#   python -m kimi_adapter.cli
# 本文件保留用于向后兼容，不再主动新增功能。

# Kimi 附件适配器：把 Claude Code 的 document 附件块转成 Kimi 支持的 text 块
# 工作方式：监听 127.0.0.1:18231，所有请求原样转发到 https://api.kimi.com/coding，
#           仅对 /v1/messages 的 JSON 请求体做附件块转换。key 不经手，直接透传请求头。
import json
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = "api.kimi.com"
UPSTREAM_PREFIX = "/coding"
LISTEN_PORT = 18231


def convert_documents(obj):
    """递归把 {type: document, source: {type: text, ...}} 转成 {type: text, text: ...}"""
    changed = 0
    if isinstance(obj, dict):
        if obj.get("type") == "document" and isinstance(obj.get("source"), dict):
            src = obj["source"]
            if src.get("type") == "text" and "data" in src:
                obj.clear()
                obj["type"] = "text"
                obj["text"] = "\n\n<附件内容>\n" + src["data"] + "\n</附件内容>\n\n"
                return 1
        for v in obj.values():
            changed += convert_documents(v)
    elif isinstance(obj, list):
        for v in obj:
            changed += convert_documents(v)
    return changed


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # 静音

    def _proxy(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None

        if body and self.path.startswith("/v1/messages"):
            try:
                payload = json.loads(body)
                n = convert_documents(payload)
                if n:
                    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                print(f"[适配器] path={self.path} 转换数={n}", flush=True)
            except Exception as e:
                print(f"[适配器] JSON解析失败: {e!r}, path={self.path}, body前100字节={body[:100]!r}", flush=True)

        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
        headers["Accept-Encoding"] = "identity"

        conn = http.client.HTTPSConnection(UPSTREAM_HOST, 443, timeout=300)
        try:
            conn.request(method, UPSTREAM_PREFIX + self.path, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ("transfer-encoding", "connection", "content-encoding", "content-length"):
                    self.send_header(k, v)
            self.send_header("Connection", "close")
            self.end_headers()
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except Exception as e:
            try:
                msg = json.dumps({"error": {"type": "adapter_error", "message": str(e)}}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(msg)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass
        finally:
            conn.close()
            self.close_connection = True

    def do_POST(self):
        self._proxy("POST")

    def do_GET(self):
        self._proxy("GET")


def _vscode_watchdog():
    """VS Code 关闭后自动退出：连续两次检测不到 Code.exe 进程就退出"""
    import os
    import subprocess
    import threading
    import time

    def watch():
        missing = 0
        while True:
            time.sleep(30)
            try:
                out = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq Code.exe", "/NH"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW).stdout  # 父进程是 pythonw 无控制台，不加此标志每 30 秒会闪一个黑框
                if "Code.exe" in out:
                    missing = 0
                else:
                    missing += 1
            except Exception:
                missing += 1
            if missing >= 2:
                print("[适配器] 检测不到 VS Code，自动退出", flush=True)
                os._exit(0)

    threading.Thread(target=watch, daemon=True).start()


if __name__ == "__main__":
    print(f"Kimi 附件适配器已启动: http://127.0.0.1:{LISTEN_PORT} -> {UPSTREAM_HOST}{UPSTREAM_PREFIX}")
    _vscode_watchdog()
    ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), Handler).serve_forever()
