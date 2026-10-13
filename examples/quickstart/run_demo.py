#!/usr/bin/env python3
"""One-click demonstration runner for KillTheHW quickstart."""
import json
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).parent
ROOT = BASE.parent.parent
SCRIPTS = ROOT / "killthehw" / "scripts"


def main():
    print("=" * 60)
    print("      KillTheHW 快速上手一键演示 (Quickstart Demo)")
    print("=" * 60)

    # 1. Check environment
    print("\n[Step 1/4] 环境体检...")
    subprocess.run([sys.executable, str(SCRIPTS / "check_env.py")], check=True)

    # 2. Ensure assets exist
    print("\n[Step 2/4] 准备模板与实验素材...")
    subprocess.run([sys.executable, str(BASE / "make_demo_assets.py")], check=True)

    # 3. Inspect template
    print("\n[Step 3/4] 解析学校 DOCX 模板结构锚点...")
    template = BASE / "template.docx"
    template_map = BASE / "template-map.json"
    if template_map.exists():
        template_map.unlink()
    subprocess.run([
        sys.executable, str(SCRIPTS / "build_report.py"), "inspect",
        str(template), "--out", str(template_map)
    ], check=True)

    # Update template_sha256 in report-plan.json
    import hashlib
    sha = hashlib.sha256(template.read_bytes()).hexdigest()
    plan_path = BASE / "report-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["template_sha256"] = sha
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. Build report
    print("\n[Step 4/4] 注入真实数据与截图，构建完整实验报告...")
    output = BASE / "output_report.docx"
    if output.exists():
        output.unlink()
    res = subprocess.run([
        sys.executable, str(SCRIPTS / "build_report.py"), "build",
        str(template), "--plan", str(plan_path), "--out", str(output)
    ], capture_output=True, text=True, check=True)
    print(res.stdout)

    print("\n" + "=" * 60)
    print("🎉 演示成功！已生成可直接编辑的实验报告:")
    print(f"   文件路径: {output.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
