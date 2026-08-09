from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .config import AppConfig
from .controller import TicketController, WorkflowError
from .device import U2Device
from .probe import classify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="android-visible-flow",
        description="通过 UIAutomator2/ADB 控制已登录的大麦 Android 真机",
    )
    parser.add_argument("--config", default="config.json", help="配置 JSON 路径")
    parser.add_argument("--inspect", action="store_true", help="只读取当前页面，不执行触摸")
    parser.add_argument("--serial", help="inspect 模式使用的设备序列号")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.inspect:
            if not args.serial:
                raise ValueError("inspect 模式需要 --serial")
            _inspect_device(U2Device(args.serial))
            return 0
        config = AppConfig.load(Path(args.config))
        device = U2Device(config.device_serial)
        controller = TicketController(config, device, logger=_print_log)
        result = controller.run()
    except (OSError, ValueError, RuntimeError, WorkflowError) as error:
        _print_log(f"失败: {error}")
        return 2

    _print_log(
        f"完成: {result.message}; 总耗时 {result.elapsed_ms} ms; 拥挤重试 {result.busy_retries} 次"
    )
    return 0


def _print_log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}", flush=True)


def _inspect_device(device: U2Device) -> None:
    snapshot = device.snapshot()
    _print_log(
        f"device={device.serial} package={snapshot.package} activity={snapshot.activity} "
        f"state={classify(snapshot).value} size={snapshot.width}x{snapshot.height}"
    )
    visible_nodes = [
        node
        for node in snapshot.nodes
        if node.text or node.description or (node.clickable and node.resource_id)
    ]
    for index, node in enumerate(visible_nodes):
        x, y = node.bounds.center
        label = node.text or node.description or node.resource_id
        _print_log(
            f"node[{index:03d}] center=({x},{y}) clickable={node.clickable} "
            f"selected={node.selected or node.checked} label={label!r}"
        )


if __name__ == "__main__":
    sys.exit(main())
