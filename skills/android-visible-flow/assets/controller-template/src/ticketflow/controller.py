from __future__ import annotations

import time
from collections.abc import Callable

from .clock import BeijingClock
from .config import AppConfig, MatchRule
from .device import DevicePort
from .model import PageState, RunResult, Snapshot, UiNode
from .probe import classify, clickable_candidates, find_any_text_node, find_text_node


class WorkflowError(RuntimeError):
    pass


class TicketController:
    def __init__(
        self,
        config: AppConfig,
        device: DevicePort,
        clock: BeijingClock | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self.device = device
        self.clock = clock or BeijingClock()
        self.log = logger or (lambda _: None)
        self._sale_wait_completed = False
        self._session_selected = False
        self._price_selected = False
        self._attendees_selected: set[str] = set()
        self._order_submit_attempts = 0
        self._busy_retries = 0
        self._last_state: PageState | None = None

    def run(self) -> RunResult:
        started = time.perf_counter()
        target = self.clock.target(self.config.sale_time)
        offset = self.clock.sync() if target is not None else 0.0
        source = ", ".join(self.clock.sources) if self.clock.sources else "Windows 系统时钟"
        self.log(f"北京时间源: {source}, 偏移 {offset * 1000:+.1f} ms")
        if target is not None:
            self.log(f"目标时间: {target.isoformat(timespec='milliseconds')}")

        unknown_count = 0
        for _ in range(240):
            snapshot = self.device.fast_snapshot()
            state = classify(snapshot)
            if state not in (PageState.DETAIL, PageState.PAYMENT, PageState.EXTERNAL):
                snapshot = self.device.snapshot()
                state = classify(snapshot)
            self._report_state(state, snapshot)

            if state is PageState.PAYMENT:
                return self._result(
                    state,
                    "已进入官方支付/收银台页面，自动流程完成并停止",
                    started,
                )

            if state is PageState.EXTERNAL and self._order_submit_attempts > 0:
                return self._result(
                    state,
                    "订单提交后已跳转到外部支付应用，自动流程停止",
                    started,
                )

            if state is PageState.VERIFICATION:
                self._wait_for_manual_verification()
                unknown_count = 0
                continue

            if state is PageState.BUSY:
                self._recover_from_busy()
                unknown_count = 0
                continue

            if state is PageState.DETAIL:
                if not self._sale_wait_completed:
                    self.clock.wait_until(target, lead_ms=self.config.lead_ms)
                    self._sale_wait_completed = True
                    self.log("进入详情页热路径")
                if not self._enter_from_detail(snapshot):
                    raise WorkflowError("详情页按钮连续触摸后仍未跳转，请检查页面或坐标比例")
                unknown_count = 0
                continue

            if state is PageState.SKU:
                self._handle_sku(snapshot)
                unknown_count = 0
                continue

            if state is PageState.ORDER:
                self._handle_order(snapshot)
                unknown_count = 0
                continue

            if state is PageState.DAMAI_OTHER:
                raise WorkflowError(
                    f"当前在大麦非目标页面: {snapshot.activity}；请先打开目标演出详情页"
                )

            unknown_count += 1
            if unknown_count >= 5:
                raise WorkflowError(
                    f"连续无法识别页面: package={snapshot.package}, activity={snapshot.activity}"
                )
            self.device.sleep(0.12)

        raise WorkflowError("状态机超过最大步骤数，已停止")

    def _enter_from_detail(self, snapshot: Snapshot) -> bool:
        semantic = find_any_text_node(
            snapshot,
            ("立即预订", "立即购买", "立即购票", "马上抢", "去抢票"),
        )
        if semantic is not None:
            point = semantic.bounds.center
            point_description = f"控件 {semantic.text or semantic.description}"
        else:
            point = (
                round(snapshot.width * self.config.detail_button.x_ratio),
                round(snapshot.height * self.config.detail_button.y_ratio),
            )
            point_description = "OPPO 底部 CTA 比例坐标"

        original_activity = snapshot.activity
        for attempt in range(1, self.config.detail_retry_count + 1):
            self.log(f"详情页触摸 {attempt}/{self.config.detail_retry_count}: {point_description} {point}")
            self.device.tap(*point)
            self.device.sleep(self.config.action_interval_ms / 1000.0)
            package, activity = self.device.current_app()
            if package != "cn.damai" or activity != original_activity:
                return True
        return False

    def _handle_sku(self, snapshot: Snapshot) -> None:
        if not self._session_selected:
            node = self._resolve_rule(snapshot, self.config.session, "session")
            if node is None:
                raise WorkflowError("SKU 页没有找到配置的场次，未执行盲点")
            if not node.selected and not node.checked:
                self.log(f"选择场次: {self.config.session.text or self.config.session.fallback_index}")
                self.device.tap(*node.bounds.center)
                self.device.sleep(self.config.action_interval_ms / 1000.0)
            self._session_selected = True
            snapshot = self.device.snapshot()
            if classify(snapshot) is not PageState.SKU:
                return

        if not self._price_selected:
            node = self._resolve_rule(snapshot, self.config.price, "price")
            if node is None:
                raise WorkflowError("SKU 页没有找到配置的票档，未执行盲点")
            if not node.selected and not node.checked:
                self.log(f"选择票档: {self.config.price.text or self.config.price.fallback_index}")
                self.device.tap(*node.bounds.center)
                self.device.sleep(self.config.action_interval_ms / 1000.0)
            self._price_selected = True
            snapshot = self.device.snapshot()
            if classify(snapshot) is not PageState.SKU:
                return

        confirm = self._bottom_action(snapshot, ("确定", "确认", "下一步"))
        if confirm is None:
            raise WorkflowError("SKU 页未找到“确定/下一步”按钮")
        self.log("确认场次和票档")
        self.device.tap(*confirm.bounds.center)
        self.device.sleep(self.config.transition_timeout_ms / 1000.0)

    def _handle_order(self, snapshot: Snapshot) -> None:
        for attendee in self.config.attendees:
            if attendee in self._attendees_selected:
                continue
            node = find_text_node(snapshot, attendee)
            if node is None:
                raise WorkflowError(f"确认订单页没有找到观演人: {attendee}")
            if not node.selected and not node.checked:
                self.log(f"选择观演人: {attendee}")
                self.device.tap(*node.bounds.center)
                self.device.sleep(self.config.action_interval_ms / 1000.0)
            self._attendees_selected.add(attendee)
            snapshot = self.device.snapshot()
            if classify(snapshot) is not PageState.ORDER:
                return

        submit = self._bottom_action(snapshot, ("提交订单", "立即支付", "确认订单"))
        if submit is None:
            raise WorkflowError("确认订单页未找到提交按钮")
        if self._order_submit_attempts >= 3:
            raise WorkflowError("提交按钮已触摸 3 次但页面没有变化")
        self._order_submit_attempts += 1
        self.log(f"提交官方订单: 第 {self._order_submit_attempts} 次")
        self.device.tap(*submit.bounds.center)
        self.device.sleep(self.config.transition_timeout_ms / 1000.0)

    def _wait_for_manual_verification(self) -> None:
        self.log("检测到官方安全验证；请在手机上完成，程序正在等待")
        deadline = time.monotonic() + self.config.verification_wait_seconds
        while time.monotonic() < deadline:
            self.device.sleep(0.35)
            snapshot = self.device.snapshot()
            if classify(snapshot) is not PageState.VERIFICATION:
                self.log("安全验证已离开，自动继续")
                return
        raise WorkflowError("等待安全验证超时")

    def _recover_from_busy(self) -> None:
        if self._busy_retries >= self.config.busy_retry_count:
            raise WorkflowError("拥挤/繁忙重试次数已用完")
        self._busy_retries += 1
        self.log(f"页面拥挤，回退重进 {self._busy_retries}/{self.config.busy_retry_count}")
        self.device.back()
        self.device.sleep(self.config.busy_retry_interval_ms / 1000.0)

        for _ in range(3):
            snapshot = self.device.snapshot()
            state = classify(snapshot)
            if state is PageState.DETAIL:
                break
            if state in (PageState.ORDER, PageState.SKU, PageState.BUSY):
                self.device.back()
                self.device.sleep(self.config.busy_retry_interval_ms / 1000.0)
                continue
            break

        self._session_selected = False
        self._price_selected = False
        self._attendees_selected.clear()
        self._order_submit_attempts = 0

    def _resolve_rule(
        self,
        snapshot: Snapshot,
        rule: MatchRule,
        kind: str,
    ) -> UiNode | None:
        if rule.text:
            node = find_text_node(snapshot, rule.text)
            if node is not None:
                return node
        if rule.fallback_index is None:
            return None
        if kind == "session":
            candidates = clickable_candidates(snapshot, 0.12, 0.50)
        else:
            candidates = clickable_candidates(snapshot, 0.28, 0.82)
        if rule.fallback_index >= len(candidates):
            return None
        return candidates[rule.fallback_index]

    @staticmethod
    def _bottom_action(snapshot: Snapshot, labels: tuple[str, ...]) -> UiNode | None:
        nodes: list[UiNode] = []
        for label in labels:
            normalized_label = "".join(label.lower().split())
            nodes.extend(
                node
                for node in snapshot.nodes
                if node.enabled
                and normalized_label in "".join(node.searchable_text.lower().split())
            )
        if not nodes:
            return None
        nodes.sort(key=lambda node: (node.bounds.center[1], node.bounds.center[0]), reverse=True)
        return nodes[0]

    def _report_state(self, state: PageState, snapshot: Snapshot) -> None:
        if state is self._last_state:
            return
        self._last_state = state
        self.log(f"页面: {state.value} | {snapshot.activity}")

    def _result(self, state: PageState, message: str, started: float) -> RunResult:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        self.log(message)
        return RunResult(
            state=state,
            message=message,
            elapsed_ms=elapsed_ms,
            busy_retries=self._busy_retries,
        )
