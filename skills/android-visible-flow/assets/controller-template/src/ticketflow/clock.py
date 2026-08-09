from __future__ import annotations

import socket
import statistics
import struct
import time
from datetime import datetime, timedelta, timezone


BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
NTP_EPOCH_DELTA = 2_208_988_800


class BeijingClock:
    """System clock with a small optional NTP offset."""

    def __init__(self) -> None:
        self.offset_seconds = 0.0
        self.sources: tuple[str, ...] = ()

    def sync(
        self,
        servers: tuple[str, ...] = ("ntp.aliyun.com", "time.cloudflare.com"),
        timeout_seconds: float = 0.45,
    ) -> float:
        samples: list[float] = []
        sources: list[str] = []
        for server in servers:
            try:
                samples.append(self._query_ntp_offset(server, timeout_seconds))
                sources.append(server)
            except OSError:
                continue
        if samples:
            self.offset_seconds = statistics.median(samples)
            self.sources = tuple(sources)
        return self.offset_seconds

    def now(self) -> datetime:
        return datetime.fromtimestamp(time.time() + self.offset_seconds, tz=BEIJING_TZ)

    def target(self, value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = value.strip().replace("Z", "+00:00")
        if "T" in normalized or "-" in normalized:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=BEIJING_TZ)
            return parsed.astimezone(BEIJING_TZ)

        formats = ("%H:%M:%S.%f", "%H:%M:%S")
        parsed_time = None
        for format_value in formats:
            try:
                parsed_time = datetime.strptime(normalized, format_value).time()
                break
            except ValueError:
                continue
        if parsed_time is None:
            raise ValueError("sale_time 应为 ISO 时间或 HH:mm:ss.SSS")
        now = self.now()
        return datetime.combine(now.date(), parsed_time, tzinfo=BEIJING_TZ)

    def wait_until(self, target: datetime | None, lead_ms: int = 0) -> None:
        if target is None:
            return
        threshold = target.timestamp() - lead_ms / 1000.0
        while True:
            remaining = threshold - (time.time() + self.offset_seconds)
            if remaining <= 0:
                return
            if remaining > 1.0:
                time.sleep(min(remaining - 0.3, 5.0))
            elif remaining > 0.08:
                time.sleep(remaining / 2.0)
            else:
                time.sleep(0.002)

    @staticmethod
    def _query_ntp_offset(server: str, timeout_seconds: float) -> float:
        packet = b"\x1b" + 47 * b"\0"
        started_wall = time.time()
        started_perf = time.perf_counter()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(timeout_seconds)
            client.sendto(packet, (server, 123))
            data, _ = client.recvfrom(48)
        elapsed = time.perf_counter() - started_perf
        if len(data) < 48:
            raise OSError("NTP response is too short")
        seconds, fraction = struct.unpack("!II", data[40:48])
        server_time = seconds - NTP_EPOCH_DELTA + fraction / 2**32
        local_midpoint = started_wall + elapsed / 2.0
        return server_time - local_midpoint

