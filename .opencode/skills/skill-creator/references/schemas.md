# 评估数据 Schema

## evals.json（测试用例）

```json
{
  "skill_name": "doc-templates",
  "description": "通知模板技能测试",
  "evals": [
    {
      "id": 1,
      "name": "起草一个会议通知",
      "prompt": "请以XX局名义起草一份关于召开2026年第二季度安全生产工作会议的通知，参会人员为各科室负责人，时间6月20日上午9点，地点3楼会议室。",
      "expected_output": "符合通知格式，包含标题、主送机关、正文（会议时间、地点、参会人员、要求）、发文机关、日期",
      "files": [],
      "assertions": [
        {
          "name": "文种正确",
          "description": "标题应包含'通知'字样",
          "type": "contains",
          "target": "通知"
        },
        {
          "name": "要素完整",
          "description": "包含会议时间要素",
          "type": "contains",
          "target": "6月20日"
        }
      ]
    }
  ]
}
```

## result.json（单次运行结果）

```json
{
  "eval_id": 1,
  "eval_name": "起草一个会议通知",
  "prompt": "用户输入的完整 prompt",
  "system_prompt": "实际发送的系统 prompt",
  "has_skill": true,
  "output": "模型生成的完整输出",
  "error": null,
  "metrics": {
    "success": true,
    "model": "deepseek-chat",
    "input_tokens": 523,
    "output_tokens": 891,
    "cost_yuan": 0.0032,
    "duration_ms": 4230.5,
    "retries_used": 0
  },
  "timestamp": "2026-06-12T11:30:00"
}
```

## summary.json（汇总报告）

```json
{
  "skill_name": "doc-templates",
  "skill_path": ".opencode/skills/doc-templates",
  "model": "deepseek-chat",
  "has_skill": true,
  "total_evals": 3,
  "success_count": 3,
  "total_cost": 0.0098,
  "total_duration_ms": 12500.0,
  "total_output_tokens": 2700,
  "results": [],
  "timestamp": "2026-06-12T11:30:00"
}
```

## assertions 类型

| type | 说明 | 参数 |
|------|------|------|
| `contains` | 输出包含指定文本 | `target`: 字符串 |
| `not_contains` | 输出不含指定文本 | `target`: 字符串 |
| `matches` | 输出匹配正则 | `pattern`: 正则字符串 |
| `format_check` | 格式合规检查 | 无（调用 doc-format 校验） |
