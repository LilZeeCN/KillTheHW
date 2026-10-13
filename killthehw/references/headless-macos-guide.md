# macOS 自动化静默执行与后台截取指南

针对理工科学生在自动化跑实验报告时的两大痛点：
1. **电脑待机休眠/熄屏**：跑大作业（如深度学习训练、Hadoop 集群执行、Wireshark 抓包）期间电脑锁屏或睡眠，导致脚本中断。
2. **截屏抢焦点弹窗与台前调度畸变**：传统 UI 自动化（如 `osascript activate`、PyAutoGUI、剪贴板粘贴）每隔几秒弹出一个窗口、夺取鼠标/键盘焦点并污染剪贴板；同时在开启 macOS **台前调度（Stage Manager）** 时，普通 `screencapture -l <WindowID>` 会截取出缩放在侧边栏的 3D 倾斜缩略图。

KillTheHW 针对 macOS 提供了真正的**零焦点抢占（Zero-Focus-Stealing）**全链路静默方案：

---

## 一、防休眠托管体系 (`caffeinate` 自动化)

KillTheHW 在底层核心（`scripts/_common.py` 与 `scripts/pty_session.py`）内置了 `caffeinate_guard` 上下文生命周期托管。

### 运行机制
- 当启动长期终端会话（PTY）或后台渲染任务时，引擎会自动通过 `caffeinate -dimsu -w <PID>` 创建系统级电源断言，阻止显示器、系统与磁盘休眠。
- **生命周期绑定**：断言与任务进程强绑定，一旦任务结束或被取消，电源断言自动退出，绝不残留后台耗电。

---

## 二、抗台前调度畸变的底层帧缓冲静默截图 (`scripts/capture_window.py`)

KillTheHW 的 `capture_window.py` 直接通过 `ctypes` 调用 `CoreGraphics` 与 `ImageIO` 底层 C API，彻底绕开窗口置顶与台前调度透视形变：

```bash
# 1. 列出当前所有窗口及其 WindowID
python3 killthehw/scripts/capture_window.py --list

# 2. 按应用名称直接捕获后台窗口（自动优选带标题的主文档窗口，无阴影、无畸变）
python3 killthehw/scripts/capture_window.py --app "Code" --out evidence/gui/vscode.png

# 3. 指定确切的 Window ID 静默抓取
python3 killthehw/scripts/capture_window.py --id 5345 --out evidence/gui/vscode.png
```

### 核心原理
- **绕过 Stage Manager 3D 透视变换**：当 macOS 开启台前调度（Stage Manager）且目标窗口退居后台侧边栏时，系统合成器会对窗口施加三维倾斜矩阵，导致常规 `screencapture -l <WindowID>` 只能截到 `280x334` 的倾斜缩略图。
- **`CGWindowListCreateImage` + `kCGWindowImageBoundsIgnoreFraming | kCGWindowImageBestResolution`**：`capture_window.py` 直接向 `WindowServer` 请求窗口原始未变换的离屏 Retina 帧缓冲（Backing Store），即使窗口被遮挡或被收纳进台前调度侧边栏，也能 100% 静默导出完整、方正的 `2940x1846` 原生 Retina 位图，全程不调用 `activate`，零焦点干扰。

---

## 三、VS Code / Cursor 零焦点后台无感控制 (`scripts/vscode_headless.py`)

针对需要在 VS Code / Cursor 界面中同时展示**编辑器代码**与**内置终端运行结果**的实验报告取证场景，严禁使用 `osascript activate` 或 `pbcopy` 抢夺用户焦点。

KillTheHW 提供了基于 Node.js Extension Host V8 Inspector 协议的纯后台控制器 `scripts/vscode_headless.py`：

```bash
# 1. 后台静默打开指定代码文件（自动清除选区高亮，不弹窗、不抢焦点）
python3 killthehw/scripts/vscode_headless.py --workspace /path/to/lab --close-others --open-file /path/to/lab/test1.py

# 2. 后台静默重置并新建干净的内置终端，直接向终端 PTY 发送执行指令
python3 killthehw/scripts/vscode_headless.py --workspace /path/to/lab --new-terminal --send-text "python test1.py"
```

### 核心原理
1. **唤醒 Extension Host 调试端口**：自动定位目标工作区对应的 `Code Helper (Plugin)`（`--inspect-port=0`）进程，通过发送 `SIGUSR1` 信号在本地回环地址 `127.0.0.1` 唤醒 V8 Inspector WebSocket 端点。
2. **注入内部 `vscode` API**：通过 WebSocket 调用 `Runtime.evaluate`，直接从模块缓存提取 `vscode` 实例，在进程内部调用 `vscode.workspace.openTextDocument`、`vscode.window.showTextDocument`、`vscode.window.createTerminal` 与 `terminal.sendText(cmd, true)`。
3. **真正零感知**：不触发 macOS 窗口激活、不移动鼠标、不模拟全局按键、不占用系统剪贴板，用户在其它窗口打字、浏览网页或全屏工作时完全无感。
