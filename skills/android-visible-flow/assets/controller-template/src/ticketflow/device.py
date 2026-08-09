from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Protocol

from .model import Bounds, Snapshot, UiNode


BOUNDS_PATTERN = re.compile(r"\[(\d+),(\d+)]\[(\d+),(\d+)]")


class DevicePort(Protocol):
    def fast_snapshot(self) -> Snapshot: ...

    def snapshot(self) -> Snapshot: ...

    def current_app(self) -> tuple[str, str]: ...

    def tap(self, x: int, y: int) -> None: ...

    def back(self) -> None: ...

    def sleep(self, seconds: float) -> None: ...


def parse_nodes(xml: str) -> tuple[UiNode, ...]:
    if not xml.strip():
        return ()
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return ()

    nodes: list[UiNode] = []
    for element in root.iter("node"):
        raw_bounds = element.attrib.get("bounds", "")
        match = BOUNDS_PATTERN.fullmatch(raw_bounds)
        if match is None:
            continue
        left, top, right, bottom = (int(value) for value in match.groups())
        if right <= left or bottom <= top:
            continue
        nodes.append(
            UiNode(
                text=element.attrib.get("text", "").strip(),
                description=element.attrib.get("content-desc", "").strip(),
                resource_id=element.attrib.get("resource-id", "").strip(),
                class_name=element.attrib.get("class", "").strip(),
                bounds=Bounds(left, top, right, bottom),
                clickable=element.attrib.get("clickable") == "true",
                enabled=element.attrib.get("enabled", "true") == "true",
                selected=element.attrib.get("selected") == "true",
                checked=element.attrib.get("checked") == "true",
            )
        )
    return tuple(nodes)


class U2Device:
    """UIAutomator2 transport. Touches are injected by the device-side agent."""

    def __init__(self, serial: str) -> None:
        try:
            import uiautomator2 as u2
        except ImportError as error:
            raise RuntimeError("尚未安装 uiautomator2，请先运行 scripts/setup.ps1") from error

        self.serial = serial
        try:
            self.driver = u2.connect(serial)
        except Exception as error:
            raise RuntimeError(
                f"无法连接 Android 设备 {serial}；请检查数据线、USB 调试和 adb devices"
            ) from error
        self.driver.settings["wait_timeout"] = 0.25
        self.driver.settings["operation_delay"] = (0, 0)
        try:
            self.driver.settings["waitForIdleTimeout"] = 0
            self.driver.settings["waitForSelectorTimeout"] = 100
        except (KeyError, TypeError):
            pass
        width, height = self.driver.window_size()
        self._width = int(width)
        self._height = int(height)

    def fast_snapshot(self) -> Snapshot:
        package, activity = self.current_app()
        return Snapshot(
            package=package,
            activity=activity,
            width=self._width,
            height=self._height,
            xml="",
            nodes=(),
        )

    def snapshot(self) -> Snapshot:
        package, activity = self.current_app()
        try:
            xml = self.driver.dump_hierarchy(compressed=True, pretty=False)
        except TypeError:
            xml = self.driver.dump_hierarchy(compressed=True)
        return Snapshot(
            package=package,
            activity=activity,
            width=self._width,
            height=self._height,
            xml=xml,
            nodes=parse_nodes(xml),
        )

    def current_app(self) -> tuple[str, str]:
        current = self.driver.app_current()
        return str(current.get("package", "")), str(current.get("activity", ""))

    def tap(self, x: int, y: int) -> None:
        self.driver.click(int(x), int(y))

    def back(self) -> None:
        self.driver.press("back")

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
