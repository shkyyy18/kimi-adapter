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
import http.client
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = "api.kimi.com"
UPSTREAM_PREFIX = "/coding"
LISTEN_PORT = 18231


def _log(msg):
    print(time.strftime("[%H:%M:%S]"), msg, flush=True)


def extract_pdf_text(b64data):
    """把 base64 编码的 PDF 提取为纯文本（需要 pypdf，未安装或解析失败时返回说明文字）"""
    try:
        import base64
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(base64.b64decode(b64data)))
        parts = []
        for i, page in enumerate(reader.pages, 1):
            parts.append(f"--- 第 {i} 页 ---\n" + (page.extract_text() or ""))
        text = "\n".join(parts).strip()
        return text or "[PDF 解析成功但未提取到文字（可能是扫描件/图片型 PDF，本适配器无法识别）]"
    except ImportError:
        return "[本机未安装 pypdf，无法解析 PDF：pip install --user pypdf]"
    except Exception as e:
        return f"[PDF 解析失败: {e!r}]"


def convert_documents(obj):
    """递归把 {type: document, source: {...}} 转成 {type: text, text: ...}
    支持 source.type=text（直接转）和 source.type=base64 的 PDF（本地提取文字后转）"""
    changed = 0
    if isinstance(obj, dict):
        if obj.get("type") == "document" and isinstance(obj.get("source"), dict):
            src = obj["source"]
            if src.get("type") == "text" and "data" in src:
                obj.clear()
                obj["type"] = "text"
                obj["text"] = "\n\n<附件内容>\n" + src["data"] + "\n</附件内容>\n\n"
                return 1
            if (
                src.get("type") == "base64"
                and src.get("media_type") == "application/pdf"
                and "data" in src
            ):
                obj.clear()
                obj["type"] = "text"
                obj["text"] = (
                    "\n\n<附件内容(PDF已提取为文本)>\n"
                    + extract_pdf_text(src["data"])
                    + "\n</附件内容>\n\n"
                )
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

        is_messages = self.path.startswith("/v1/messages")
        is_stream = False
        if body and is_messages:
            try:
                payload = json.loads(body)
                is_stream = bool(payload.get("stream"))
                n = convert_documents(payload)
                if n:
                    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                _log(f"path={self.path} 转换数={n} 流式={is_stream}")
            except Exception as e:
                _log(f"JSON解析失败: {e!r}, path={self.path}, body前100字节={body[:100]!r}")

        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in ("host", "content-length", "connection", "accept-encoding")
        }
        headers["Accept-Encoding"] = "identity"

        if is_messages and method == "POST":
            self._proxy_buffered(method, body, headers, is_stream)
        else:
            self._proxy_passthrough(method, body, headers)
        self.close_connection = True

    @staticmethod
    def _stream_complete(data):
        # SSE 流完整性：收到 message_stop 或 [DONE] 才算完整
        return b"message_stop" in data or b"[DONE]" in data

    def _proxy_buffered(self, method, body, headers, is_stream):
        """缓冲转发：完整收完上游响应、校验完整后才一次性发给客户端；
        中途断流/出错自动重试（最多3次），前端不会再看到半截 JSON（Unterminated string）。
        代价：失去逐字流式输出，结果一次性出现。"""
        last_err = None
        for attempt in range(3):
            conn = None
            try:
                conn = http.client.HTTPSConnection(UPSTREAM_HOST, 443, timeout=300)
                conn.request(method, UPSTREAM_PREFIX + self.path, body=body, headers=headers)
                resp = conn.getresponse()
                chunks = []
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                data = b"".join(chunks)
                if resp.status == 200 and is_stream and not self._stream_complete(data):
                    raise RuntimeError(f"流式响应不完整({len(data)}字节, 无 message_stop)")
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in (
                        "transfer-encoding",
                        "connection",
                        "content-encoding",
                        "content-length",
                    ):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
                if attempt:
                    _log(f"path={self.path} 第{attempt + 1}次尝试后成功")
                return
            except Exception as e:
                last_err = e
                _log(f"上游失败(第{attempt + 1}/3次): {e!r}, path={self.path}")
                time.sleep(1.0 + attempt)
            finally:
                if conn:
                    conn.close()
        # 三次都失败：此时还没向客户端发任何内容，回干净的 502（不再是半截 JSON）
        _log(f"path={self.path} 重试3次均失败: {last_err!r}")
        try:
            msg = json.dumps(
                {
                    "error": {
                        "type": "adapter_error",
                        "message": (f"upstream failed after 3 attempts: {last_err}"),
                    }
                }
            ).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(msg)
        except Exception:
            pass

    def _proxy_passthrough(self, method, body, headers):
        """非 /v1/messages 请求：直接转发（量小，不做缓冲重试）"""
        conn = http.client.HTTPSConnection(UPSTREAM_HOST, 443, timeout=300)
        sent = False
        try:
            conn.request(method, UPSTREAM_PREFIX + self.path, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in (
                    "transfer-encoding",
                    "connection",
                    "content-encoding",
                    "content-length",
                ):
                    self.send_header(k, v)
            self.send_header("Connection", "close")
            self.end_headers()
            sent = True
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except Exception as e:
            _log(f"上游转发异常: {e!r}, path={self.path}, 已发送部分响应={sent}")
            if not sent:
                try:
                    msg = json.dumps(
                        {"error": {"type": "adapter_error", "message": str(e)}}
                    ).encode()
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
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,  # pythonw 无控制台，防闪黑框
                ).stdout
                if "Code.exe" in out:
                    missing = 0
                else:
                    missing += 1
            except Exception:
                missing += 1
            if missing >= 2:
                _log("检测不到 VS Code，自动退出")
                os._exit(0)

    threading.Thread(target=watch, daemon=True).start()


if __name__ == "__main__":
    # 包（kimi_adapter/）可导入时，直接复用包入口：--help 及全部 CLI 参数行为一致
    try:
        from kimi_adapter.cli import main as _pkg_main
    except ImportError:
        _pkg_main = None

    if _pkg_main is not None:
        _pkg_main()
    else:
        # 纯单文件场景（脱离仓库单独分发）：无包可用，退化为本文件内置服务器。
        # 至少响应 --help/-h，避免不解析参数、无提示地阻塞。
        import sys

        if any(a in ("-h", "--help") for a in sys.argv[1:]):
            print(
                "用法: python kimi-adapter.py [-h]\n"
                "\n"
                "Kimi 附件适配器（单文件 legacy 版）：启动后监听 "
                f"127.0.0.1:{LISTEN_PORT}，转发到 {UPSTREAM_HOST}{UPSTREAM_PREFIX}。\n"
                "本版本不支持命令行参数；如需 --host/--port/--config 等参数，"
                "请使用包入口：\n"
                "  pip install -e .\n"
                "  python -m kimi_adapter.cli --help"
            )
            sys.exit(0)
        _log(
            f"Kimi 附件适配器已启动: http://127.0.0.1:{LISTEN_PORT}"
            f" -> {UPSTREAM_HOST}{UPSTREAM_PREFIX}"
        )
        _vscode_watchdog()
        ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), Handler).serve_forever()
