---
name: android-visible-flow
description: Build, rebrand, debug, and validate PC-driven Android visible-UI automation with ADB/UIAutomator2, Activity-based page probing, coordinate fallbacks, selector actions, timed starts, and recovery state machines. Use when Codex needs to create or repair a non-root Android controller that operates an already signed-in app through visible screens, especially ticket checkout flows where AccessibilityService gestures are ignored.
---

# Android Visible Flow

Build Android automation as a PC-side controller connected to a real, non-root device. Keep authentication inside the official app and operate only visible UI.

## Workflow

1. Confirm the target Android package, device model, screen size, current Activities, expected page sequence, and user-selected options.
2. Read [references/architecture.md](references/architecture.md) before changing transport, page detection, hot-path timing, or recovery behavior.
3. Copy `assets/controller-template/` into a clean project directory. Do not copy `.venv`, caches, screenshots, APKs, credentials, or device-specific `config.json` files.
4. Rename the package and command only when requested. Keep controller, device transport, page probe, config, and models as separate modules.
5. Install dependencies with `setup.cmd`. Run `test.cmd` before connecting a device.
6. Connect exactly one authorized Android device. Confirm it appears in `adb devices`, then run `inspect.cmd <serial>` to collect the current Activity and visible selectors without touching the screen.
7. Adapt Activity markers, text selectors, coordinate ratios, and recovery markers from inspection evidence. Prefer text or resource IDs; use coordinates only as measured fallback values.
8. Put slow hierarchy reads outside the first-click hot path. On a known detail Activity, use the cached screen size and measured CTA coordinate, then wait for an Activity transition.
9. Run the controller only after configuration validation. Record state transitions, coordinates, retries, and final handoff state.
10. Stop on an official verification challenge for manual completion. Do not reverse private APIs, forge queue credentials, bypass CAPTCHA or device risk controls, or automate final payment confirmation.

## Validation

- Run `test.cmd` after every state-machine or selector change.
- Test page classification before action ordering.
- Test the full fake-device path from detail to payment handoff.
- Test busy-page recovery and verification waiting independently.
- On a real device, inspect first and use a non-purchasing page or mock target until coordinates are confirmed.
- Treat an AccessibilityService gesture completion callback as delivery evidence only; verify that the target Activity actually changed.

## Resources

- `assets/controller-template/`: reusable Python 3.10+ and UIAutomator2 controller project.
- `references/architecture.md`: transport choices, page-state design, performance rules, and adaptation checklist.

