# AndroidVisibleFlow

`AndroidVisibleFlow` is a reusable Codex Skill and controller template for PC-driven Android visible-UI workflows. It uses ADB/UIAutomator2 with a real, non-root Android device, Activity-based page detection, selector actions, measured coordinate fallbacks, timed starts, and recovery state machines.

The bundled controller template is tuned for a ticket checkout flow while keeping device transport, page probing, configuration, and orchestration separate for adaptation to other Android apps.

## Skill location

```text
skills/android-visible-flow/
├── SKILL.md
├── agents/openai.yaml
├── references/architecture.md
└── assets/controller-template/
```

Install or copy the `skills/android-visible-flow` directory into your Codex skills directory, then invoke it as `$android-visible-flow`.

Example:

```text
Use $android-visible-flow to create a Windows controller for my non-root Android device,
inspect the current Activities, implement a visible page-state workflow, and validate it
with a fake-device test before real-device testing.
```

## Controller requirements

- Windows with Python 3.10–3.13
- Android Platform Tools and an authorized `adb devices` connection
- Android real device with USB or wireless debugging
- Official target app already signed in

The template does not reverse private APIs, forge queue credentials, bypass CAPTCHA/device controls, or confirm final payment.

