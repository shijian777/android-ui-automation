from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PageState(str, Enum):
    DETAIL = "detail"
    SKU = "sku"
    ORDER = "order"
    BUSY = "busy"
    VERIFICATION = "verification"
    PAYMENT = "payment"
    DAMAI_OTHER = "damai_other"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


@dataclass(frozen=True)
class UiNode:
    text: str
    description: str
    resource_id: str
    class_name: str
    bounds: Bounds
    clickable: bool
    enabled: bool
    selected: bool
    checked: bool

    @property
    def searchable_text(self) -> str:
        return " ".join(
            part for part in (self.text, self.description, self.resource_id) if part
        ).lower()


@dataclass(frozen=True)
class Snapshot:
    package: str
    activity: str
    width: int
    height: int
    xml: str
    nodes: tuple[UiNode, ...]

    @property
    def visible_text(self) -> str:
        return " ".join(node.searchable_text for node in self.nodes)


@dataclass(frozen=True)
class RunResult:
    state: PageState
    message: str
    elapsed_ms: int
    busy_retries: int

