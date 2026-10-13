# 任务记录

适用于多文件、多小问、电脑操作和需要恢复的作业。记录是执行账本，不是要求用户填写的表格。Agent 在执行时维护它，不让用户重复提供已知信息。

## 目录与脚本

```text
work/<job-id>/
  job.json
  actions.jsonl
  extracted/<input-id>/
  evidence/
  deliverables/
  completion.md
```

```bash
python3 <skill目录>/scripts/inspect_inputs.py --job-dir /绝对路径/work/hw01 /绝对路径/作业.docx /绝对路径/课件目录
python3 <skill目录>/scripts/extract_materials.py /绝对路径/work/hw01
python3 <skill目录>/scripts/check_deliverables.py /绝对路径/work/hw01
```

初始化保存原文件路径和 SHA-256，不移动或改写原件。必要转换保留在 extracted，交付物放 deliverables。原文件不可访问时先恢复原件或请用户补充，不悄悄认定未变。只在需要时创建 completion.md，记录完成项、文件和阻塞。

多实验共用环境且连续交付时，用单个 job 下的多个 assignment，例如实验一到五；每份报告关联自己的要求和 checks，共用材料不重复登记。任务环境或交付终点明显独立时再拆 job。assignment 与 task 的关联可经 requirements 追溯。

actions.jsonl 按里程碑批量记录，不要求逐键登记；任务完成、环境修复、输入/文件变更和交付边界是典型里程碑。阻塞或即将中断时及时落盘；批记可使用 started_at/ended_at 标明实际时间范围，不把补记时间当成所有动作发生时间。每行一个 JSON 事件，包含 `time/task_id/action/observed/evidence`。时间用含时区的 ISO 8601。记录真实观察，不记录密码或完整登录令牌。

## job.json 约定

初始化会填好 schema_version、job_id、inputs 与空数组。Agent 填写下列内容；ID 在本任务内唯一。路径除 inputs[].path 外均相对任务目录。

| 字段 | 内容 |
| --- | --- |
| inputs | `id/path/kind/sha256/size`；填 role（assignment/template/reference/data/excluded）、review.status（pending/complete）、review.sha256、review.scope（实际阅读范围或排除理由）。extraction 由提取器维护；review 在实际阅读后填写。 |
| assignments | `id/title/source`，来源含材料与具体位置。 |
| requirements | `id/assignment_id/text/source/task_ids/check_ids`；required 默认 true。source 含 input_id/locator，从用户消息得来时写 conversation 及简短原意。 |
| tasks | `id/title/requirement_ids/status`；状态 planned/running/blocked/complete/skipped。选做题用 selected；未选任务写 selected:false 与 reason。 |
| deliverables | `id/path/sha256/status/requirement_ids/check_ids/required_check_kinds`；状态 draft/verified。核验种类按产物选 content、visual、execution、calculation 等。 |
| checks | `id/kind/status/method/result/subjects/evidence/input_hashes`；状态 passed/failed/pending。subjects 是 `[{path,sha256}]`；evidence 为真实日志、复算、阅读或视觉核验记录的相对路径数组；input_hashes 将本项核验用到的 input ID 映射到当时来源散列值。 |
| issues | `id/detail/blocking/resolved`；影响正确交付的缺口才设 blocking。 |
| delivery | target 为 local/upload/submit，state 为 draft/local_ready/uploaded/submitted/submission_unknown，scope 记录用户授权原意。平台目标另写 destination 和 receipts。 |
| writing_profile | 可选：本次文体、课程深度、样文来源、语气、保留术语、格式约束。仅存在本任务。 |

receipts 每项含 `state/destination/observed_at/evidence/deliverable_ids/subjects`，对应实际看到的上传或提交结果。evidence 为本地平台状态记录或截图路径数组。subjects 用与 checks 相同格式绑定实际上传的文件版本。destination 可写作业页面 URL，避免保存会话凭据。

示例片段（合并进初始化记录，值由本次实际结果填写）：

```json
{
  "tasks": [{"id":"T1","title":"完成数据统计","requirement_ids":["R1"],"status":"complete"}],
  "deliverables": [{"id":"D1","path":"deliverables/统计.csv","sha256":"实际文件散列值","status":"verified","requirement_ids":["R1"],"check_ids":["C1"],"required_check_kinds":["calculation"]}],
  "checks": [{"id":"C1","kind":"calculation","status":"passed","method":"从原始各行独立复算总和与均值","result":"逐项一致","subjects":[{"path":"deliverables/统计.csv","sha256":"实际文件散列值"}],"evidence":["evidence/recalculation.txt"],"input_hashes":{"I001":"实际来源散列值"}}]
}
```

## 覆盖与恢复

- 每条必做要求关联已完成任务和通过的实质核验；只做风格检查不能验证一道题。
- 选做 N 题：把选择 N 题记为必做要求，将选题和数量记入核验。未选题写 reason，不算缺交。不要随意把困难题设为 optional。
- 教材只读相关章节时，在 review.scope 写清范围；complete 表示本次所需阅读已完成，不表示逐字读完整本书。要求和评分标准须完整阅读。
- 新材料用新 input ID 补充路径、类型、散列值和 pending review，再运行提取；不要重新初始化覆盖账本。
- 原件改变时先比对要求，更新 input.sha256/size 并重置 review，重新提取；重审受影响任务。变化涉及全局要求时重审全部任务。
- 文件被改动时更新 deliverable.sha256，重做相关 checks；不能只改旧核验的散列值。
- 检查器无法识别编造的 passed。Agent 必须真实执行并保留足以复核的依据。

## 批量登记与 ID

先用 `register_requirements.py draft <job> --input I001 --assignment-key lab1 --title 实验一 --out lab1-draft.json` 生成候选。默认识别阿拉伯数字及中文全角题号：`3.`、`1、`、`（1）`、`(2)`、`一、`、`（一）` 等；其他风格（字母小问 `(a)`、`第1题` 等）自定义 `--pattern`，需包含 number 与 text 命名组，例如 `--pattern '^(?P<number>[（(][a-z][)）])\s*(?P<text>.+)$'`。候选可能混入续行、说明或选做规则，Agent 对照原材料审阅后再导入，不要求用户做机械登记。复杂表格或混合编号可以直接整理批次 JSON。

```json
{
  "assignment":{"key":"lab1","title":"实验一","source":{"input_id":"I001","locator":"PDF 第 1 页"}},
  "input_hashes":{"I001":"实际来源散列值"},
  "requirements":[
    {"key":"1a","number":"1(a)","text":"建立目标表","source":{"input_id":"I001","locator":"PDF 第 2 页 1(a)"},"task_key":"table-work","task_title":"建表与查询","check_kind":"execution"},
    {"key":"1b","number":"1(b)","text":"执行查询并记录结果","source":{"input_id":"I001","locator":"PDF 第 2 页 1(b)"},"task_key":"table-work","check_kind":"execution"}
  ]
}
```

使用 `register_requirements.py import <job> lab1-draft.json --dry-run` 查看关联，去掉 dry-run 原子保存。脚本分配 A/R/T/C 编号，输出 requirement、task、check 映射；同一个 assignment key 与 task_key 合并任务。复制映射填 deliverables，不再手工猜 check ID。所有新增 task 为 planned、check 为 pending，登记不能算完成。

重复导入完全相同的批次会复用 ID，不重置已有结果；相同 key 的要求内容改变则拒绝静默覆盖，需要显式修改既有记录并重审相关核验。旧账本和自由命名 ID 继续有效，工具会避开已占用 ID。

job.json 保持单一写入者，独立工作者可提供候选批次和证据，由主 Agent 合并；原子保存不等于支持多个进程同时编辑同一本账本。
