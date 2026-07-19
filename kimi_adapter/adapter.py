"""Core proxy and document-conversion logic for Kimi Adapter."""

from __future__ import annotations

import http.client
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

logger = logging.getLogger(__name__)


def convert_documents(obj: Any) -> int:
    """Recursively convert Claude 'document' content blocks to plain text blocks.

    Claude Code sends text attachments as:
        {"type": "document", "source": {"type": "text", "data": "..."}}

    Kimi's Anthropic-compatible gateway does not accept the 'document' block.
    This converts it to:
        {"type": "text", "text": "\\n\\n<附件内容>\\n...\\n</附件内容>\\n\\n"}

    Returns the number of blocks converted.
    """
    changed = 0
    if isinstance(obj, dict):
        if obj.get("type") == "document" and isinstance(obj.get("source"), dict):
            src = obj["source"]
            if src.get("type") == "text" and "data" in src:
                obj.clear()
                obj["type"] = "text"
                obj["text"] = "\n\n<附件内容>\n" + src["data"] + "\n</附件内容>\n\n"
                return 1
        for value in obj.values():
            changed += convert_documents(value)
    elif isinstance(obj, list):
        for value in obj:
            changed += convert_documents(value)
    return changed


def make_handler(
    *,
    upstream_host: str,
    upstream_prefix: str,
    upstream_scheme: str = "https",
    silent: bool = False,
):
    """Factory for the request handler with runtime upstream settings."""

    class ProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            if not silent:
                super().log_message(fmt, *args)

        def do_GET(self) -> None:  # noqa: N802
            self._proxy("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._proxy("POST")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._proxy("OPTIONS")

        def _proxy(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None

            if body and self.path.startswith("/v1/messages"):
                try:
                    payload = json.loads(body)
                    n = convert_documents(payload)
                    if n:
                        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    logger.debug("path=%s converted=%d", self.path, n)
                except json.JSONDecodeError as exc:
                    logger.warning("JSON parse failed: %s", exc)

            headers = {
                k: v
                for k, v in self.headers.items()
                if k.lower() not in ("host", "content-length", "connection", "accept-encoding")
            }
            headers["Accept-Encoding"] = "identity"

            if upstream_scheme == "https":
                conn = http.client.HTTPSConnection(upstream_host, 443, timeout=300)
            else:
                conn = http.client.HTTPConnection(upstream_host, 80, timeout=300)

            try:
                conn.request(method, upstream_prefix + self.path, body=body, headers=headers)
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
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Proxy error: %s", exc)
                try:
                    msg = json.dumps(
                        {"error": {"type": "adapter_error", "message": str(exc)}}
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
                self.close_connection = True

    return ProxyHandler


def start_vscode_watchdog() -> None:
    """Exit the process when VS Code is no longer running.

    This is useful when the adapter is launched as a VS Code background task:
    the adapter starts with VS Code and stops shortly after VS Code closes,
    avoiding a lingering background process.
    """
    import os
    import subprocess
    import threading
    import time

    def watch() -> None:
        missing = 0
        while True:
            time.sleep(30)
            try:
                out = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq Code.exe", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,  # type: ignore[attr-defined]
                ).stdout
                if "Code.exe" in out:
                    missing = 0
                else:
                    missing += 1
            except Exception:
                missing += 1
            if missing >= 2:
                logger.info("VS Code not detected, exiting watchdog.")
                os._exit(0)

    threading.Thread(target=watch, daemon=True).start()


def run_server(config: Any) -> None:
    """Start the adapter server with the given config-like object."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    handler = make_handler(
        upstream_host=config.upstream_host,
        upstream_prefix=config.upstream_prefix,
        upstream_scheme=getattr(config, "upstream_scheme", "https"),
        silent=config.silent,
    )

    server = ThreadingHTTPServer((config.listen_host, config.listen_port), handler)
    logger.info(
        "Kimi Adapter listening on http://%s:%d -> %s%s",
        config.listen_host,
        config.listen_port,
        config.upstream_host,
        config.upstream_prefix,
    )

    if config.vscode_watchdog:
        try:
            start_vscode_watchdog()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not start VS Code watchdog: %s", exc)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()
