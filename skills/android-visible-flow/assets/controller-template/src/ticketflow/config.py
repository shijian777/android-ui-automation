from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MatchRule:
    text: str = ""
    fallback_index: int | None = None

    @classmethod
    def from_mapping(cls, value: Any, name: str) -> "MatchRule":
        if not isinstance(value, dict):
            raise ValueError(f"{name} 必须是 JSON 对象")
        text = str(value.get("text", "")).strip()
        raw_index = value.get("fallback_index")
        index = None if raw_index is None else int(raw_index)
        if not text and index is None:
            raise ValueError(f"{name} 至少需要 text 或 fallback_index")
        if index is not None and index < 0:
            raise ValueError(f"{name}.fallback_index 不能小于 0")
        return cls(text=text, fallback_index=index)


@dataclass(frozen=True)
class PointRatio:
    x_ratio: float = 0.720
    y_ratio: float = 0.932

    @classmethod
    def from_mapping(cls, value: Any) -> "PointRatio":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("detail_button 必须是 JSON 对象")
        result = cls(
            x_ratio=float(value.get("x_ratio", cls.x_ratio)),
            y_ratio=float(value.get("y_ratio", cls.y_ratio)),
        )
        if not 0.0 < result.x_ratio < 1.0 or not 0.0 < result.y_ratio < 1.0:
            raise ValueError("detail_button 坐标比例必须在 0 和 1 之间")
        return result


@dataclass(frozen=True)
class AppConfig:
    device_serial: str
    sale_time: str | None
    session: MatchRule
    price: MatchRule
    attendees: tuple[str, ...]
    detail_button: PointRatio = field(default_factory=PointRatio)
    lead_ms: int = 350
    action_interval_ms: int = 70
    transition_timeout_ms: int = 1400
    detail_retry_count: int = 6
    busy_retry_count: int = 20
    busy_retry_interval_ms: int = 160
    verification_wait_seconds: int = 180

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        config_path = Path(path)
        with config_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("配置根节点必须是 JSON 对象")

        attendees = tuple(
            str(item).strip() for item in raw.get("attendees", []) if str(item).strip()
        )
        if not attendees:
            raise ValueError("attendees 至少要填写一个已保存的观演人姓名")
        if any("替换" in name or "观演人姓名" in name for name in attendees):
            raise ValueError("请先把 attendees 示例文字替换成真实姓名")

        serial = str(raw.get("device_serial", "")).strip()
        if not serial:
            raise ValueError("device_serial 不能为空")

        config = cls(
            device_serial=serial,
            sale_time=(str(raw["sale_time"]).strip() if raw.get("sale_time") else None),
            session=MatchRule.from_mapping(raw.get("session", {}), "session"),
            price=MatchRule.from_mapping(raw.get("price", {}), "price"),
            attendees=attendees,
            detail_button=PointRatio.from_mapping(raw.get("detail_button")),
            lead_ms=int(raw.get("lead_ms", 350)),
            action_interval_ms=int(raw.get("action_interval_ms", 70)),
            transition_timeout_ms=int(raw.get("transition_timeout_ms", 1400)),
            detail_retry_count=int(raw.get("detail_retry_count", 6)),
            busy_retry_count=int(raw.get("busy_retry_count", 20)),
            busy_retry_interval_ms=int(raw.get("busy_retry_interval_ms", 160)),
            verification_wait_seconds=int(raw.get("verification_wait_seconds", 180)),
        )
        config._validate_ranges()
        return config

    def _validate_ranges(self) -> None:
        ranges = {
            "lead_ms": (self.lead_ms, 0, 5000),
            "action_interval_ms": (self.action_interval_ms, 20, 1000),
            "transition_timeout_ms": (self.transition_timeout_ms, 200, 10000),
            "detail_retry_count": (self.detail_retry_count, 1, 30),
            "busy_retry_count": (self.busy_retry_count, 0, 100),
            "busy_retry_interval_ms": (self.busy_retry_interval_ms, 50, 5000),
            "verification_wait_seconds": (self.verification_wait_seconds, 5, 900),
        }
        for name, (value, minimum, maximum) in ranges.items():
            if not minimum <= value <= maximum:
                raise ValueError(f"{name} 必须在 {minimum} 到 {maximum} 之间")

