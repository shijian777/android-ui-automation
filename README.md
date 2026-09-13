# Android 可视化自动操作工具

让电脑通过 ADB 和 UIAutomator2 操作真实 Android 手机界面，支持页面识别、控件点击、坐标补充、定时开始和异常恢复。本项目独立保存可复用技能与控制器模板；内置示例围绕票务结算流程，需要按目标应用适配后再验证。

## 文件与功能

- `skills/android-visible-flow/SKILL.md`：使用流程与约束。
- `skills/android-visible-flow/agents/openai.yaml`：技能的界面展示配置。
- `skills/android-visible-flow/references/architecture.md`：控制器架构说明。
- `skills/android-visible-flow/assets/controller-template/`：Python 设备连接、页面探测、配置和任务执行模板。

仓库统一命名为 `android-ui-automation`；技能调用名 `$android-visible-flow` 保持兼容。以下保留安装和设备要求。

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
