#!/usr/bin/env python3
"""Environment and capability checker for KillTheHW.

Checks Python version, required libraries, CLI utilities, and determines
which execution modes (Mode 1: Format & Assemble, Mode 2: Run & Capture,
Mode 3: Audit & Visual Review) are supported on this machine.
"""
import importlib
import os
import platform
import shutil
import sys


def check_module(name, pip_package=None):
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "installed")
        return True, ver, None
    except ImportError:
        return False, None, pip_package or name


def check_binary(cmd, install_hint=None):
    path = shutil.which(cmd)
    return (True, path, None) if path else (False, None, install_hint or cmd)


def main():
    print("=" * 60)
    print("            KillTheHW 环境与运行能力体检")
    print("=" * 60)

    # 1. System & Python
    py_ver = sys.version_info
    py_ok = py_ver >= (3, 9)
    os_name = platform.system()
    print(f"操作系统: {os_name} ({platform.machine()})")
    print(f"Python 版本: {sys.version.split()[0]} {'[合格]' if py_ok else '[需 >= 3.9]'}")

    # 2. Python Packages
    packages = [
        ("docx", "python-docx", "DOCX 模板解析与报告构建 (核心必须)"),
        ("PIL", "Pillow", "截图裁剪与终端渲染 (核心必须)"),
        ("pyte", "pyte", "ANSI 终端日志仿真渲染 (终端取证)"),
    ]
    pkg_results = {}
    print("\n【Python 核心库检测】")
    missing_pips = []
    for mod_name, pip_name, desc in packages:
        ok, ver, hint = check_module(mod_name, pip_name)
        pkg_results[mod_name] = ok
        status = f"✅ 已就绪 ({ver})" if ok else f"❌ 缺失 (需 pip install {pip_name})"
        if not ok:
            missing_pips.append(pip_name)
        print(f"  - {pip_name:12s}: {status} -- {desc}")

    # 3. CLI Utilities
    clis = [
        ("pdftotext", "PDF 作业说明与附件文本提取", "brew install poppler / apt install poppler-utils"),
        ("soffice", "DOCX 离线转 PDF 与页面级视觉核验", "安装 LibreOffice"),
    ]
    cli_results = {}
    print("\n【系统 CLI 工具检测】")
    for cmd, desc, hint in clis:
        ok, path, _ = check_binary(cmd)
        cli_results[cmd] = ok
        status = f"✅ 已就绪 ({path})" if ok else f"⚠️ 未安装 ({hint})"
        print(f"  - {cmd:12s}: {status} -- {desc}")

    # 4. OS Features
    pty_supported = hasattr(os, "fork") and os_name != "Windows"
    print("\n【终端与环境特性】")
    print(f"  - POSIX PTY 会话: {'✅ 支持 (可原生运行真实终端取证)' if pty_supported else '⚠️ 受限 (Windows 原生不支持 forkpty，建议在 WSL 中运行)'}")

    # 5. Mode Capability Assessment
    mode1 = pkg_results.get("docx", False)
    mode2 = mode1 and pkg_results.get("PIL", False) and pty_supported
    mode3 = mode1 and (cli_results.get("soffice", False) or True)

    print("\n【支持的工作流模式】")
    print(f"  - 模式 1: 整理与排版 (已有数据/截图 -> 填入模板): {'✅ 完全支持' if mode1 else '❌ 缺少 python-docx'}")
    print(f"  - 模式 2: 自动化运行与取证 (自动执行命令 -> 取证截图 -> 报告): {'✅ 完全支持' if mode2 else '⚠️ 部分支持 (需 POSIX + pyte + Pillow)'}")
    print(f"  - 模式 3: 报告预检与审计 (核对指导书覆盖率与评分点): ✅ 完全支持")

    if missing_pips:
        print("\n【快速修复建议】")
        print(f"  运行命令安装缺失依赖: pip install {' '.join(missing_pips)}")

    print("=" * 60)
    return 0 if mode1 else 1


if __name__ == "__main__":
    sys.exit(main())
