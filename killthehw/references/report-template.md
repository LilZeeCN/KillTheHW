# 使用学校的 DOCX 模板构建报告

先查看模板所有页面，再用 build_report.py 导出结构清单。模板控制版式，脚本只填指定位置，不重新设计报告。模板、填充计划和本次内容分开保存；每份实验报告从原模板构建，不能拿上一次成品反复追加。

```bash
python3 <skill>/scripts/build_report.py inspect 模板.docx --out template-map.json
python3 <skill>/scripts/build_report.py build 模板.docx --plan report-plan.json --out 实验一报告.docx
```

需要 python-docx。优先宿主提供的文档运行环境；否则使用已有虚拟环境，或通过正规包管理器准备依赖。不把某台机器的 Python 路径写死进本 Skill。

## 结构清单与填充计划

清单包含模板 SHA-256、原始位置 ID、文本、样式、图片数量和 XML 路径。`B` 是正文顶层块，`P` 是段落，`CELL` 是实际 XML 单元格；合并单元格按实际节点登记。ID 仅在该模板版本有效，不把后来重新编号的 ID 混进同一计划。遇到多个同名“实验内容”，靠位置和上下文确定目标。

```json
{
  "template_sha256": "从清单复制的散列值",
  "replacements": [
    {"token":"{{姓名}}","value":"用户提供的姓名","expected_count":1}
  ],
  "fields": [
    {"target":"CELL0004","expect":"学号：____","text":"学号：用户提供的学号"}
  ],
  "sections": [
    {
      "start":"B0003","end":"B0008","expect":"实验内容","heading":"实验内容与结果",
      "blocks":[
        {"type":"paragraph","text":"根据真实执行记录填写。","style_from":"P0007"},
        {"type":"code","file":"query.sql","font_size":9},
        {"type":"image","path":"evidence/query.png","width_cm":14,"caption":"图 1 查询结果","evidence_kind":"ui_screenshot"}
      ]
    }
  ],
  "remove_blocks":["B0010"],
  "forbid_text":["请在此处填写","{{姓名}}","此处插入示例截图"]
}
```

示例 ID 不能照抄，必须来自实际清单。图片、代码和 provenance 文件路径相对计划文件；也可使用明确的绝对路径。按页面可用宽度确定图片尺寸。

- replacements 用于普通文字占位符，支持占位符被拆成多个 run，并保留相邻字体格式；expected_count 防止漏填和意外多处替换。
- fields 精确替换一个段落或单元格，expect 校验旧内容；单元格保留边框、合并和首段/首 run 的格式，其原有文字、图和嵌套内容会被替换。不能用 fields 修改应保留的复杂单元格。
- sections 保留 start 标题和 end 边界，替换中间全部正文块，包括无文字的占位图。end 可为 END，表示正文末尾的节属性之前。多个区域先在原模板上解析，再执行；重叠和颠倒范围会报错。
- remove_blocks 仅删除清单中明确指定的正文顶层块。不能靠“没有文字”批量删段，因为图片也可能放在空段里。
- style_from 复用模板段落的段落/首 run 格式；也可显式指定存在的 style。标题改写保留标题段原样式。
- 显式格式配置：在 paragraph 或 code 块中支持覆盖格式（如 `"font":"Times New Roman"`, `"font_eastasia":"宋体"`, `"font_size":10.5`, `"line_spacing":1.5`, `"alignment":"left"`, `"bold":false`），自动注入 XML 复合字体，确保在跨平台 Office/WPS 打开时不降级。
- forbid_text 由 Agent 从实际模板挑选占位提示，不能把“实验”“示例”等正常用词列成通用黑名单。

构建器拒绝模板版本变化、字段不匹配、错误范围、跨节属性删除和覆盖已有文件。修改计划后输出新版本。目录、交叉引用、复杂内容控件、修订、浮动对象及嵌入文件须额外核对，不能把脚本当作完整 Word 排版引擎。

## PTY 结果图与报告

图注默认省略：caption 仅在模板本身使用图注体系或题目要求时填写，普通"运行结果"截图直接贴图。PTY 渲染图使用 `evidence_kind:"pty_rendered"`，并设置 `provenance` 为 render_terminal.py 生成的同名 JSON。渲染默认保留 ANSI 配色（与真实终端观感一致），`--monochrome` 可改为单色，两种模式的 provenance 与披露要求一致。构建器核对图片、原始日志快照与会话记录的散列值，并自动在图注追加“真实终端日志渲染，非屏幕截图”。不得为了满足题目截图要求改成 ui_screenshot。

## 交付前

重新提取成品核对小节顺序、封面信息、代码和图注；查看每页，确认占位文字/示例图已移除、图片清楚、公式和表格未截断。未修改的页眉页脚、样式、节设置和其他模板资源应保留。构建完成返回 visual_review:pending，只有真实看过排版后才能核验完成。

实现依据：[python-docx 文本对象](https://python-docx.readthedocs.io/en/latest/api/text.html)、[文档编辑用法](https://python-docx.readthedocs.io/en/latest/user/quickstart.html)。
