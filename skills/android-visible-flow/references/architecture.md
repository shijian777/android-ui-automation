# Architecture reference

## Layers

Keep four layers independent:

1. `device.py`: UIAutomator2 connection, fast Activity reads, hierarchy snapshots, touch injection, Back, and sleep.
2. `probe.py`: pure classification from package, Activity, and visible nodes.
3. `controller.py`: deterministic page-state transitions and recovery.
4. `config.py`: device serial, timing, selectors, coordinate fallbacks, and retry limits.

This separation allows fake-device tests without ADB and lets a new ticket app replace its probe rules without rewriting transport.

## Transport choice

Use a PC-side UIAutomator2/ADB controller when a non-root app's AccessibilityService gesture is accepted by Android but ignored by the target app. UIAutomator2 still requires USB or wireless debugging and a computer; do not present it as a standalone APK.

Do not substitute captured private endpoints for visible UI. A URL alone does not provide authorized signatures, session state, risk tokens, or queue credentials.

## Hot path

- Connect and initialize UIAutomator2 before the target time.
- Cache screen dimensions during device setup.
- Read only the current Activity on the known detail page.
- Avoid hierarchy dumps before the first CTA touch when the CTA is hidden from the accessibility tree.
- Use a measured `(x_ratio, y_ratio)` fallback that scales to the same device resolution family.
- After each touch, check package and Activity before retrying.
- Dump the hierarchy once after entering option or order pages, then resolve several actions from that snapshot when possible.
- Keep retry intervals bounded; faster polling is not proof of higher success and may trigger platform controls.

## Page precedence

Classify in this order:

1. Verification or security challenge.
2. Busy, crowded, or transient error.
3. Payment or external handoff.
4. Known detail Activity.
5. Order confirmation.
6. SKU, session, or price selection.
7. Other target-app page.
8. Unknown or external page.

Use the known detail Activity before broad markers such as `tradeorder`; some detail Activity namespaces contain that substring.

## Selection rules

- Prefer exact normalized text.
- Fall back to text containment when formatting varies.
- Use resource IDs when stable and visible.
- Use an index only within a constrained screen region and only after inspection.
- Refuse a missing attendee or price instead of clicking an unrelated control.
- Choose the bottom-most matching action for duplicated labels such as `确定` or `提交订单`.

## Recovery

On a busy page, press Back and re-probe. Continue backing through order and SKU pages until detail is reached, then clear cached selection state and re-enter. Bound retries in configuration and log every recovery.

On verification, wait for the user to complete the official challenge and continue only after the page state changes. Never simulate or solve the challenge.

Stop when the official payment Activity or an external payment app opens. Leave financial confirmation to the user.

## Adaptation checklist

- Target package and launch behavior.
- Detail, SKU, order, verification, busy, and payment Activities.
- Screen dimensions and system insets.
- CTA coordinate ratio measured from a successful ADB/UIAutomator2 touch.
- Session and price labels or resource IDs.
- Attendee selection behavior and checked state.
- Submit label and payment handoff behavior.
- Back-stack behavior after a crowded-page error.
- Unit tests for every newly observed state.

