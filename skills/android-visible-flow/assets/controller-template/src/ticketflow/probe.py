from __future__ import annotations

from .model import PageState, Snapshot, UiNode


BUSY_MARKERS = (
    "访问人数过多",
    "人数较多",
    "太拥挤",
    "系统繁忙",
    "稍后重试",
    "前方拥堵",
    "网络开小差",
    "抢票人数太多",
)
VERIFICATION_MARKERS = ("滑动验证", "安全验证", "请完成验证", "验证码", "拖动滑块")
PAYMENT_MARKERS = ("收银台", "支付方式", "确认付款", "支付宝", "云闪付")
ORDER_MARKERS = ("确认订单", "提交订单", "立即支付", "观演人")
SKU_MARKERS = ("选择票档", "选择场次", "票档", "确定")


def classify(snapshot: Snapshot) -> PageState:
    package = snapshot.package.lower()
    activity = snapshot.activity.lower()
    visible = snapshot.visible_text

    if package and package != "cn.damai":
        return PageState.EXTERNAL
    if _contains_any(activity, ("captcha", "verify", "security", "containeractivity")) or _contains_any(
        visible, VERIFICATION_MARKERS
    ):
        return PageState.VERIFICATION
    if _contains_any(visible, BUSY_MARKERS):
        return PageState.BUSY
    if _contains_any(activity, ("cashier", "payment", "payactivity")) or _contains_any(
        visible, PAYMENT_MARKERS
    ):
        return PageState.PAYMENT
    if "projectdetailactivity" in activity:
        return PageState.DETAIL
    if _contains_any(activity, ("orderconfirm", "tradeorder", "orderdetail")) or _contains_any(
        visible, ORDER_MARKERS
    ):
        return PageState.ORDER
    if _contains_any(activity, ("ncovsku", "skuactivity", "sku.")) or _contains_any(
        visible, SKU_MARKERS
    ):
        return PageState.SKU
    if package == "cn.damai":
        return PageState.DAMAI_OTHER
    return PageState.UNKNOWN


def find_text_node(snapshot: Snapshot, text: str) -> UiNode | None:
    target = normalize(text)
    if not target:
        return None
    candidates = [
        node for node in snapshot.nodes if node.enabled and target in normalize(node.searchable_text)
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda node: (
            0 if normalize(node.text) == target else 1,
            0 if node.clickable else 1,
            node.bounds.width * node.bounds.height,
        )
    )
    return candidates[0]


def find_any_text_node(snapshot: Snapshot, values: tuple[str, ...]) -> UiNode | None:
    for value in values:
        node = find_text_node(snapshot, value)
        if node is not None:
            return node
    return None


def clickable_candidates(
    snapshot: Snapshot,
    y_min_ratio: float,
    y_max_ratio: float,
) -> list[UiNode]:
    minimum_y = snapshot.height * y_min_ratio
    maximum_y = snapshot.height * y_max_ratio
    result = []
    for node in snapshot.nodes:
        center_x, center_y = node.bounds.center
        if not node.enabled or not node.clickable:
            continue
        if not minimum_y <= center_y <= maximum_y:
            continue
        if node.bounds.width < 36 or node.bounds.height < 28:
            continue
        if node.bounds.width >= snapshot.width * 0.96:
            continue
        if center_x < 0 or center_x > snapshot.width:
            continue
        result.append(node)
    result.sort(key=lambda node: (node.bounds.center[1], node.bounds.center[0]))
    return _deduplicate_by_center(result)


def normalize(value: str) -> str:
    return "".join(value.lower().split()).replace("￥", "¥")


def _contains_any(value: str, markers: tuple[str, ...]) -> bool:
    normalized = normalize(value)
    return any(normalize(marker) in normalized for marker in markers)


def _deduplicate_by_center(nodes: list[UiNode]) -> list[UiNode]:
    result: list[UiNode] = []
    seen: set[tuple[int, int]] = set()
    for node in nodes:
        x, y = node.bounds.center
        bucket = (x // 12, y // 12)
        if bucket in seen:
            continue
        seen.add(bucket)
        result.append(node)
    return result
