from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ticketflow.clock import BeijingClock
from ticketflow.config import AppConfig, MatchRule, PointRatio
from ticketflow.controller import TicketController
from ticketflow.device import parse_nodes
from ticketflow.model import PageState, Snapshot
from ticketflow.probe import classify


def make_xml(*nodes: tuple[str, str, bool]) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?><hierarchy>']
    for index, (text, bounds, clickable) in enumerate(nodes):
        parts.append(
            '<node index="{index}" text="{text}" resource-id="" class="android.view.View" '
            'content-desc="" clickable="{clickable}" enabled="true" selected="false" '
            'checked="false" bounds="{bounds}" />'.format(
                index=index,
                text=text,
                clickable=str(clickable).lower(),
                bounds=bounds,
            )
        )
    parts.append("</hierarchy>")
    return "".join(parts)


def snapshot(activity: str, *nodes: tuple[str, str, bool]) -> Snapshot:
    xml = make_xml(*nodes)
    return Snapshot(
        package="cn.damai",
        activity=activity,
        width=1080,
        height=2412,
        xml=xml,
        nodes=parse_nodes(xml),
    )


class FakeClock(BeijingClock):
    def sync(self, *args, **kwargs) -> float:
        return 0.0

    def wait_until(self, target, lead_ms=0) -> None:
        return None


class ScriptedDevice:
    def __init__(self) -> None:
        self.index = 0
        self.taps: list[tuple[int, int]] = []
        self.back_count = 0
        sku_activity = "cn.damai.commonbusiness.seatbiz.sku.qilin.ui.NcovSkuActivity"
        order_activity = "cn.damai.trade.newtradeorder.ui.order.OrderConfirmActivity"
        self.frames = [
            snapshot("cn.damai.trade.newtradeorder.ui.projectdetail.ui.activity.ProjectDetailActivity"),
            snapshot(
                sku_activity,
                ("选择场次", "[0,150][1080,250]", False),
                ("08月10日", "[100,300][500,430]", True),
                ("780元", "[100,800][420,940]", True),
                ("确定", "[520,2180][1050,2350]", True),
            ),
            snapshot(
                sku_activity,
                ("08月10日", "[100,300][500,430]", True),
                ("780元", "[100,800][420,940]", True),
                ("确定", "[520,2180][1050,2350]", True),
            ),
            snapshot(
                sku_activity,
                ("08月10日", "[100,300][500,430]", True),
                ("780元", "[100,800][420,940]", True),
                ("确定", "[520,2180][1050,2350]", True),
            ),
            snapshot(
                order_activity,
                ("确认订单", "[0,100][1080,220]", False),
                ("张三", "[100,650][500,760]", True),
                ("提交订单", "[500,2180][1050,2350]", True),
            ),
            snapshot(
                order_activity,
                ("确认订单", "[0,100][1080,220]", False),
                ("张三", "[100,650][500,760]", True),
                ("提交订单", "[500,2180][1050,2350]", True),
            ),
            snapshot(
                "cn.damai.trade.cashier.CashierActivity",
                ("支付方式", "[100,300][600,430]", False),
            ),
        ]

    def snapshot(self) -> Snapshot:
        return self.frames[self.index]

    def fast_snapshot(self) -> Snapshot:
        frame = self.frames[self.index]
        return Snapshot(
            package=frame.package,
            activity=frame.activity,
            width=frame.width,
            height=frame.height,
            xml="",
            nodes=(),
        )

    def current_app(self) -> tuple[str, str]:
        frame = self.frames[self.index]
        return frame.package, frame.activity

    def tap(self, x: int, y: int) -> None:
        self.taps.append((x, y))
        if self.index < len(self.frames) - 1:
            self.index += 1

    def back(self) -> None:
        self.back_count += 1

    def sleep(self, seconds: float) -> None:
        return None


class WorkflowTests(unittest.TestCase):
    def test_visible_flow_reaches_payment_and_stops(self) -> None:
        config = AppConfig(
            device_serial="TEST",
            sale_time=None,
            session=MatchRule(text="08月10日", fallback_index=0),
            price=MatchRule(text="780", fallback_index=0),
            attendees=("张三",),
            detail_button=PointRatio(),
        )
        device = ScriptedDevice()
        logs: list[str] = []

        result = TicketController(
            config,
            device,
            clock=FakeClock(),
            logger=logs.append,
        ).run()

        self.assertEqual(result.state, PageState.PAYMENT)
        self.assertEqual(device.taps[0], (778, 2248))
        self.assertEqual(len(device.taps), 6)
        self.assertTrue(any("选择票档" in line for line in logs))
        self.assertTrue(any("选择观演人" in line for line in logs))

    def test_probe_detects_busy_before_order(self) -> None:
        frame = snapshot(
            "cn.damai.trade.newtradeorder.ui.order.OrderConfirmActivity",
            ("当前访问人数过多，请稍后重试", "[50,500][1000,800]", False),
        )
        self.assertEqual(classify(frame), PageState.BUSY)

    def test_config_rejects_placeholder_attendee(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                '{"device_serial":"X","session":{"text":"A"},'
                '"price":{"text":"780"},"attendees":["请替换观演人姓名"]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "替换"):
                AppConfig.load(path)


if __name__ == "__main__":
    unittest.main()
