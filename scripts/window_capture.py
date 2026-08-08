from __future__ import annotations

import argparse
import json
import sys
import time
from ctypes import WINFUNCTYPE, byref, create_unicode_buffer, windll
from ctypes import wintypes
from pathlib import Path
from typing import Any

from PIL import ImageGrab


def _set_dpi_awareness() -> None:
    try:
        windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _window_text(hwnd: int) -> str:
    length = windll.user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = create_unicode_buffer(length + 1)
    windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _class_name(hwnd: int) -> str:
    buffer = create_unicode_buffer(256)
    windll.user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def _rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    windll.user32.GetWindowRect(hwnd, byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def list_windows() -> list[dict[str, Any]]:
    _set_dpi_awareness()
    rows: list[dict[str, Any]] = []

    enum_proc_type = WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _lparam: int) -> bool:
        if not windll.user32.IsWindowVisible(hwnd):
            return True
        title = _window_text(hwnd)
        if not title.strip():
            return True
        pid = wintypes.DWORD()
        windll.user32.GetWindowThreadProcessId(hwnd, byref(pid))
        left, top, right, bottom = _rect(hwnd)
        rows.append(
            {
                "hwnd": int(hwnd),
                "pid": int(pid.value),
                "title": title,
                "class_name": _class_name(hwnd),
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": right - left,
                "height": bottom - top,
            }
        )
        return True

    windll.user32.EnumWindows(enum_proc_type(callback), 0)
    return rows


def find_window(title_contains: str) -> dict[str, Any]:
    needle = title_contains.casefold()
    matches = [row for row in list_windows() if needle in row["title"].casefold()]
    if len(matches) != 1:
        raise SystemExit(
            json.dumps(
                {
                    "error": "expected_exactly_one_window",
                    "title_contains": title_contains,
                    "match_count": len(matches),
                    "matches": matches,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return matches[0]


def capture_window(title_contains: str, out: Path, method: str = "window") -> dict[str, Any]:
    _set_dpi_awareness()
    window = find_window(title_contains)
    hwnd = int(window["hwnd"])
    windll.user32.ShowWindow(hwnd, 9)
    windll.user32.BringWindowToTop(hwnd)
    windll.user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    window = find_window(title_contains)
    hwnd = int(window["hwnd"])

    if method == "window":
        image = ImageGrab.grab(window=hwnd, include_layered_windows=True)
    elif method == "bbox":
        bbox = (window["left"], window["top"], window["right"], window["bottom"])
        image = ImageGrab.grab(bbox=bbox, include_layered_windows=True, all_screens=True)
    elif method == "fullscreen":
        image = ImageGrab.grab(include_layered_windows=True, all_screens=True)
    else:
        raise ValueError(f"unknown capture method: {method}")

    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return {
        "status": "ok",
        "method": method,
        "out": str(out),
        "image_width": image.width,
        "image_height": image.height,
        "window": window,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="List and capture Windows application windows.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")

    capture = sub.add_parser("capture")
    capture.add_argument("--title", required=True)
    capture.add_argument("--out", required=True)
    capture.add_argument("--method", choices=["window", "bbox", "fullscreen"], default="window")

    args = parser.parse_args()
    if args.cmd == "list":
        print(json.dumps(list_windows(), ensure_ascii=False, indent=2))
    elif args.cmd == "capture":
        result = capture_window(args.title, Path(args.out), args.method)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
