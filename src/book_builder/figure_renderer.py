"""用 Chrome DevTools Protocol 将 HTML 插图渲染为出版用 PNG。"""

from __future__ import annotations

import base64
import json
import os
import re
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from book_builder.log import get_logger
from book_builder.pdf import _find_chrome

logger = get_logger("figure_renderer")


@dataclass(frozen=True)
class FigureRenderResult:
    source: Path
    output: Path
    width: int
    height: int


class _WebSocket:
    def __init__(self, url: str) -> None:
        parsed = urlparse(url)
        self._socket = socket.create_connection((parsed.hostname, parsed.port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {parsed.path or '/'}{('?' + parsed.query) if parsed.query else ''} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self._socket.sendall(request.encode("ascii"))
        response = self._receive_until(b"\r\n\r\n")
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError("无法建立 Chrome DevTools WebSocket 连接")

    def close(self) -> None:
        self._socket.close()

    def send_json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        header = bytearray([0x81])
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
        self._socket.sendall(header + masked)

    def receive_json(self) -> dict[str, Any]:
        fragments = bytearray()
        while True:
            first, second = self._receive_exact(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._receive_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._receive_exact(8))[0]
            if second & 0x80:
                mask = self._receive_exact(4)
                payload = bytes(
                    value ^ mask[index % 4]
                    for index, value in enumerate(self._receive_exact(length))
                )
            else:
                payload = self._receive_exact(length)
            if opcode == 0x8:
                raise RuntimeError("Chrome DevTools WebSocket 已关闭")
            if opcode == 0x9:
                self._send_control(0xA, payload)
                continue
            fragments.extend(payload)
            if first & 0x80:
                return json.loads(fragments.decode("utf-8"))

    def _send_control(self, opcode: int, payload: bytes) -> None:
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self._socket.sendall(bytes([0x80 | opcode, 0x80 | len(payload)]) + mask + masked)

    def _receive_until(self, marker: bytes) -> bytes:
        data = bytearray()
        while marker not in data:
            chunk = self._socket.recv(4096)
            if not chunk:
                raise RuntimeError("Chrome DevTools 连接意外中断")
            data.extend(chunk)
        return bytes(data)

    def _receive_exact(self, length: int) -> bytes:
        data = bytearray()
        while len(data) < length:
            chunk = self._socket.recv(length - len(data))
            if not chunk:
                raise RuntimeError("Chrome DevTools 连接意外中断")
            data.extend(chunk)
        return bytes(data)


class _ChromeSession:
    def __init__(self, chrome_bin: str | None = None) -> None:
        chrome = chrome_bin or _find_chrome()
        if chrome is None:
            raise RuntimeError("未找到 Chrome/Edge，无法导出插图 PNG。")
        self._profile = tempfile.TemporaryDirectory(prefix="book-figures-chrome-")
        self._process = subprocess.Popen(
            [
                chrome,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--hide-scrollbars",
                "--remote-debugging-port=0",
                "--remote-allow-origins=*",
                f"--user-data-dir={self._profile.name}",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        browser_url = self._read_debugger_url()
        port = urlparse(browser_url).port
        if port is None:
            raise RuntimeError("Chrome 未返回 DevTools 端口")
        page_url = self._wait_for_page_target(port)
        self._socket = _WebSocket(page_url)
        self._next_id = 0
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 2000, "height": 1200, "deviceScaleFactor": 1, "mobile": False},
        )

    def close(self) -> None:
        self._socket.close()
        self._process.terminate()
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=5)
        self._profile.cleanup()

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        call_id = self._next_id
        self._socket.send_json({"id": call_id, "method": method, "params": params or {}})
        while True:
            message = self._socket.receive_json()
            if message.get("id") != call_id:
                continue
            if "error" in message:
                raise RuntimeError(f"Chrome DevTools 调用失败 {method}: {message['error']}")
            return message.get("result", {})

    def render(self, source: Path, output: Path, export_width: int) -> FigureRenderResult:
        self.call("Page.navigate", {"url": source.resolve().as_uri()})
        self._wait_until_ready()
        metrics = self._evaluate(_FIGURE_METRICS_SCRIPT)
        if metrics["width"] <= 0 or metrics["height"] <= 0:
            raise RuntimeError(f"导出区域尺寸无效: {source}")
        if metrics["overflowX"] > 1 or metrics["overflowY"] > 1:
            raise RuntimeError(
                f"导出区域存在溢出: {source} "
                f"(x={metrics['overflowX']:.1f}, y={metrics['overflowY']:.1f})"
            )
        scale = export_width / metrics["width"]
        screenshot = self.call(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "fromSurface": True,
                "clip": {
                    "x": metrics["x"],
                    "y": metrics["y"],
                    "width": metrics["width"],
                    "height": metrics["height"],
                    "scale": scale,
                },
            },
        )
        data = base64.b64decode(screenshot["data"])
        width, height = _png_dimensions(data)
        if width != export_width:
            raise RuntimeError(f"PNG 宽度异常: {source}，预期 {export_width}，实际 {width}")
        if height < 200 or height > export_width * 2:
            raise RuntimeError(f"PNG 高度异常: {source}，实际 {height}")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".png.tmp")
        temporary.write_bytes(data)
        temporary.replace(output)
        return FigureRenderResult(source=source, output=output, width=width, height=height)

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            ready = self._evaluate(
                "document.readyState === 'complete' && "
                "(!document.fonts || document.fonts.status === 'loaded')"
            )
            if ready:
                return
            time.sleep(0.05)
        raise RuntimeError("等待插图页面加载超时")

    def _evaluate(self, expression: str) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        exception = result.get("exceptionDetails")
        if exception:
            raise RuntimeError(f"插图页面脚本执行失败: {exception}")
        return result["result"].get("value")

    def _read_debugger_url(self) -> str:
        assert self._process.stderr is not None
        deadline = time.monotonic() + 20
        stderr_buf: list[str] = []
        while time.monotonic() < deadline:
            line = self._process.stderr.readline()
            if line:
                stderr_buf.append(line)
            match = re.search(r"DevTools listening on (ws://\S+)", line)
            if match:
                return match.group(1)
            if self._process.poll() is not None:
                break
        raise RuntimeError(
            "启动 Chrome DevTools 失败。Chrome stderr 末尾:\n"
            + "".join(stderr_buf[-15:])
        )

    @staticmethod
    def _wait_for_page_target(port: int) -> str:
        deadline = time.monotonic() + 20
        endpoint = f"http://127.0.0.1:{port}/json/list"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(endpoint, timeout=2) as response:
                    targets = json.load(response)
                for target in targets:
                    if target.get("type") == "page":
                        return str(target["webSocketDebuggerUrl"])
            except OSError:
                pass
            time.sleep(0.05)
        raise RuntimeError("无法获取 Chrome 页面调试目标")


_FIGURE_METRICS_SCRIPT = """
(() => {
  const root = document.querySelector('[data-figure-root]')
    || document.querySelector('main.page')
    || document.querySelector('body > svg')
    || document.body;
  const rect = root.getBoundingClientRect();
  const overflowX = Math.max(0, root.scrollWidth - rect.width);
  const overflowY = Math.max(0, root.scrollHeight - rect.height);
  return {
    x: rect.left + window.scrollX,
    y: rect.top + window.scrollY,
    width: rect.width,
    height: rect.height,
    overflowX,
    overflowY
  };
})()
"""


def render_figure_directory(
    source_dir: str | Path,
    output_dir: str | Path,
    *,
    export_width: int = 2400,
    chapter: int | None = None,
    figure_id: str | None = None,
    chrome_bin: str | None = None,
) -> list[FigureRenderResult]:
    """批量渲染插图目录，并保持 chapter-XX 子目录结构。"""
    if export_width < 1200:
        raise ValueError("导出宽度不得小于 1200px")
    source_root = Path(source_dir)
    if not source_root.exists():
        raise FileNotFoundError(f"插图源目录不存在: {source_root}")
    pattern = f"chapter-{chapter:02d}" if chapter is not None else "chapter-*"
    sources = sorted(source_root.glob(f"{pattern}/*.html"))
    if figure_id:
        sources = [source for source in sources if source.stem == figure_id]
    if not sources:
        raise FileNotFoundError("没有找到符合条件的 HTML 插图")

    output_root = Path(output_dir)
    session = _ChromeSession(chrome_bin)
    results: list[FigureRenderResult] = []
    failures: list[str] = []
    try:
        for source in sources:
            output = output_root / source.parent.name / f"{source.stem}.png"
            try:
                result = session.render(source, output, export_width)
                results.append(result)
                logger.info("插图导出: %s (%dx%d)", result.output, result.width, result.height)
            except Exception as exc:
                failures.append(f"{source}: {exc}")
                logger.error("插图导出失败: %s", failures[-1])
    finally:
        session.close()
    if failures:
        raise RuntimeError("插图导出失败:\n" + "\n".join(failures))
    return results


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError("Chrome 返回的不是有效 PNG")
    return struct.unpack("!II", data[16:24])
