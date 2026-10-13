# KillTheHW：工科实验报告自动化与审计引擎 🚀

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
  <img src="https://img.shields.io/badge/Tests-17%20Passed-brightgreen.svg" alt="Tests" />
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20WSL-orange.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/Antigravity-Agent%20Skill-purple.svg" alt="Skill" />
</p>

<p align="center">
  <strong>拒绝格式主义内耗，把时间还给真实学习。</strong><br>
  专为工科/计算机大学生打造：原生 Word 模板保版、自动截图取证、评分点查漏预检与去 AI 化文风。
</p>

---

## 💡 为什么需要 KillTheHW？

计算机与工科大学生的日常痛点：
- 😫 **实验 10 分钟做完，贴图排版 2 小时**：终端里反复截图、裁剪、改宋体五号、1.5 倍行距、表头加粗；
- 😱 **防不胜防的漏题扣分**：指导书角落里的第 3 道思考题没看到，或者某张截图漏了关键参数，直接扣 20 分；
- 🤖 **通用 AI 的灾难味儿**：“综上所述、不仅如此、通过本次实验我深刻领悟了系统架构之美”……助教一眼打回；
- 💥 **学校模板一碰就崩**：学校发下来的古董 Word 模板，一粘贴文字，封面下划线变形、表格边框消失、排版全乱。

**KillTheHW** 是一个专为 AI Agent（如 Antigravity / Claude / ChatGPT）打造的标准工作流技能（Agent Skill），**通过底层 DOCX XML 锚点保护、PTY 终端会话取证、真实调试记录注入与评分标准比对，把实验报告变成一条清晰严谨的工程流水线**。

---

## ✨ 核心特性

| 特性 | 描述 |
| :--- | :--- |
| 🛡️ **原生模板无损保版** | 基于底层 OpenXML 锚点精准注入，封面表格、合并单元格、红头格式原汁原味继承；支持 `"style_from": "REF:Pxxxx"` 100% 像素级克隆往期满分报告的 `<w:pPr>` 与 `<w:rPr>` 排版基因。 |
| 👻 **V8 零焦点后台幽灵控制** | `vscode_headless.py` 通过 `SIGUSR1` 唤醒 VS Code / Cursor 扩展宿主 V8 Inspector，纯原生 WebSocket 注入内部 API，免弹窗、不抢焦点、零剪贴板污染完成后台代码打开与内置终端执行。 |
| 🖥️ **穿透台前调度 Retina 显存直抽** | `capture_window.py` 基于 `ctypes` 直调 macOS `CoreGraphics.framework` (`CGWindowListCreateImage`)，绕过 Stage Manager 3D 透视畸变，静默导出无阴影原生 Retina 位图。 |
| 🔤 **复合中西字体对齐** | 原生注入 `w:eastAsia`（宋体/黑体）与 `w:ascii`（Times New Roman/Courier New），跨 macOS / Windows / WPS 打开永不降级。 |
| 📸 **持久 PTY 与防休眠守护** | 支持 POSIX 持久 PTY 终端会话与 `caffeinate -dimsu -w <PID>` 进程级防休眠断言，跑长任务不锁屏、不中断，严格绑定题号与要求 ID。 |
| ✍️ **去 AI 化「偷懒减法法则」** | 严控字数强对齐往期报告，严禁在正文中复读截图已有的代码参数与张量维度，禁用斜体图注下标，还原真实工科生极简表达。 |
| 📋 **助教视角查漏预检** | 一键生成《交付预检审计单》，严格对比指导书评分点与 SHA-256 证据链，提前拦截漏答思考题与占位符残留。 |

---

## 🚦 三大使用模式

KillTheHW 适配不同阶段的作业状态：

```
┌────────────────────────────────────────────────────────────────────────┐
│                          KillTheHW 执行路由                            │
└────────────────────────────────────────────────────────────────────────┘
  ├── 模式 1【整理与保版】: 已有数据/截图/日志 ──► 匹配小节与模板 ──► 生成 DOCX
  ├── 模式 2【运行与取证】: 有指导书与代码项目 ──► PTY/CU操作取证 ──► 组装报告
  └── 模式 3【预检与审计】: 已有报告草稿 ──────► 对照评分点查漏 ──► 输出审计单
```

1. **模式 1：整理与保版装配（Format & Assemble）**
   * *“我自己做完了，这是 5 张截图和运行结果，帮我排进学校模板里并调好字体。”*
2. **模式 2：全流程运行与取证（Run & Evidence Capture）**
   * *“这是实验指导书和代码仓库，你来跑、截对应窗口的图，并整理进报告。”*
3. **模式 3：报告预检与审计（Audit & Rubric Check）**
   * *“这是我写好的实验报告，对照指导书看看我有没有漏答思考题或格式不符。”*

---

## ⚡ 1 分钟快速上手

### 1. 环境准备
```bash
git clone https://github.com/LilZeeCN/KillTheHW.git
cd KillTheHW

# 安装核心依赖
pip install python-docx Pillow pyte
```

### 2. 运行环境体检
检测你的环境支持哪些模式：
```bash
python3 killthehw/scripts/check_env.py
```
*输出示例：*
```text
============================================================
            KillTheHW 环境与运行能力体检
============================================================
操作系统: Darwin (arm64)
Python 版本: 3.13 [合格]

【Python 核心库检测】
  - python-docx : ✅ 已就绪 -- DOCX 模板解析与报告构建
  - Pillow      : ✅ 已就绪 -- 截图裁剪与渲染
  - pyte        : ✅ 已就绪 -- 终端日志仿真渲染

【支持的工作流模式】
  - 模式 1: 整理与排版: ✅ 完全支持
  - 模式 2: 自动化运行与取证: ✅ 完全支持
  - 模式 3: 报告预检与审计: ✅ 完全支持
============================================================
```

### 3. 一键体验官方 Demo
```bash
python3 examples/quickstart/run_demo.py
```
几秒内将在 `examples/quickstart/` 目录下生成一份带封面表格、题号截图对齐、思考题与真实小结的 `output_report.docx`！

---

## 🤖 在 AI Agent 中作为 Skill 使用

KillTheHW 遵循标准 [Agent Skills 规范](https://agentskills.io/)。

1. **加载 Skill**：
   将 `killthehw/` 目录软链接或复制到你的 Agent skills 路径（例如 `~/.gemini/config/skills/killthehw`）。
2. **对话提示示例**：
   > “使用 $killthehw 读取当前目录下的《实验指导书.pdf》和《学校实验模板.docx》，整理本次 Linux 网络实验报告，检查思考题覆盖情况。”

---

## 🏫 高校“课程模板包 (Course Pack)”计划

不同高校同一门课（如操作系统、计算机网络、数据库原理）的实验内容高度重合。我们发起**“一校一课一包”**计划！

如果你把你们学校某门课的模板结构或流程跑通了，欢迎提交 PR 贡献到 `templates/` 目录：
- 🏛️ **华中科技大学 (HUST)**：OS / 计网实验模板 (征集中...)
- 🏛️ **哈尔滨工业大学 (HIT)**：操作系统实验模板 (征集中...)
- 🏛️ **浙江大学 (ZJU)**：数据库系统实验模板 (征集中...)
- 🏛️ **电子科技大学 (UESTC)**：Linux 常用命令模板 (征集中...)

*欢迎通过 Issue 或 Pull Request 贡献你们学校的报告模板！合并后你的名字将进入 Contributor 榜单！*

---

## 🧪 测试与质量保证

本项目包含严格的单元测试与回归套件：
```bash
python3 -m unittest discover -s tests
```
覆盖 XML 锚点注入、PTY 真实执行隔离、东亚字体复合注入以及审计报告输出。

---

## 📜 学术诚信与免责声明 (Academic Integrity)

1. 本项目旨在**消除文档排版、截图尺寸微调等繁琐无意义的格式内耗**，辅助学生提高实验记录效率与自我审计能力。
2. 实验的核心是知识学习与代码实践。用户应严格遵守所在高校与学术机构的学生行为守则与学术诚信规范。
3. 请勿将本项目用于考试、违规代写或任何侵犯学术诚信的场景。

---

## 📄 开源许可证

本项目基于 [MIT 许可证](LICENSE) 开源。欢迎 Star 🌟 与 Fork！
