---
name: skill-creator
description: |
  公文技能创建、迭代与基准测试工具。
  提供：技能目录结构规范、SKILL.md 模板、评估维度框架、evals 运行脚本、baseline/with-skill 对比测试流程。
  适用：创建新公文技能时、修改/优化现有技能时、运行基准测试评估效果时、编写 eval 测试用例时。
  不适用：日常公文起草、常规校对。
  关键词触发：创建技能、测试技能、评估技能、技能基准、技能迭代、技能优化、evals、benchmark。
  注意：此技能专门针对本项目已有公文技能体系（doc-format/doc-proofread/doc-style/doc-templates/等），
  不适用于创建与公文无关的技能。创建新技能时必须结合本项目知识库和实际工作流。
---

# 公文技能创建与评估工具

本项目已预装 6 个公文写作技能（doc-format、doc-proofread、doc-rag、doc-style、doc-templates、official-document-writing）。本技能（skill-creator）负责：

1. 创建新的公文技能
2. 对现有技能进行测试/评估/迭代
3. 优化技能描述词以提升触发准确率

---

## 一、创建新技能

### 1.1 访谈确认需求

动笔前，通过问答确认以下内容：

| 问题 | 目的 |
|------|------|
| 这个技能要解决什么具体问题？ | 明确边界，避免与现有技能重叠 |
| 什么时候该触发？（用户说什么关键词时） | 确定 description 触发条件 |
| 输出格式是什么？ | 明确 deliverables |
| 依赖哪些现有工具/库？ | 确定 scripts/ 需要捆绑什么 |
| 需要参考哪些知识库范文？ | 确定 references/ 文件清单 |
| 是否可客观验证？ | 决定是否需要 evals + 断言 |

### 1.2 技能目录结构

```
skills/新技能名/
├── SKILL.md（必需）
│   ├── YAML frontmatter（name + description 必需）
│   └── Markdown 正文
├── scripts/（可选）  — 确定性/重复性任务的执行脚本
├── references/（可选）— 按需加载到上下文的参考文档
└── assets/（可选）   — 模板、图标、字体等输出用文件
```

### 1.3 编写 SKILL.md 规范

- **name**: 英文短横线命名，如 `doc-format`
- **description**: 包含"何时触发"和"做什么"两部分，稍"激进"以防止欠触发
- **正文**: 使用祈使句，优先解释"为什么"而不是堆砌 MUST/Never
- **渐进式披露**: 主文件控制在 300 行以内；大块参考内容放到 references/
- **引用现有技能**: 如果新技能是某个技能的子流程，在 SKILL.md 中显式写明"配合 XXX 技能使用"

**展示格式示例**：
```markdown
## 输出格式
必须使用以下模板：
# [标题]
## 一、背景
## 二、主要内容
## 三、相关要求
```

### 1.4 编写测试用例

创建 `evals/evals.json`，格式如下：

```json
{
  "skill_name": "doc-xxx",
  "evals": [
    {
      "id": 1,
      "name": "简要描述测试场景",
      "prompt": "用户输入原文",
      "expected_output": "期望结果的文字描述",
      "files": [],
      "assertions": [
        {
          "name": "检查项名称",
          "description": "具体检查什么",
          "type": "contains|not_contains|matches|format_check"
        }
      ]
    }
  ]
}
```

---

## 二、技能评估与基准测试

### 2.1 整体流程

```
创建/修改技能草案
    ↓
编写测试用例 → 保存到 skills/技能名/evals/evals.json
    ↓
并行运行测试（带技能 vs 不带技能/旧版本）
    ↓
启动 Viewer 让人类评审输出
    ↓
根据反馈迭代技能 → 重新测试
    ↓
（可选）优化 description → 重复
```

### 2.2 测试运行

使用本项目 `scripts/skill_runner.py` 运行测试：

```bash
python scripts/skill_runner.py \
  --skill-path ".opencode/skills/目标技能" \
  --evals ".opencode/skills/目标技能/evals/evals.json" \
  --output-dir "evals-results/iteration-1"
```

同时运行 **baseline**（不带技能）作为对照：
```bash
python scripts/skill_runner.py \
  --evals ".opencode/skills/目标技能/evals/evals.json" \
  --output-dir "evals-results/iteration-1/baseline"
```

### 2.3 评估维度（适用于公文技能）

对公文技能，建议从以下维度评估：

| 维度 | 权重 | 检查方法 |
|------|------|---------|
| 格式合规（GB/T 9704-2012） | 30% | doc-format 校验脚本 |
| 文种判断准确性 | 15% | 人工判断 |
| 语言规范（无 AI 腔） | 20% | doc-style 检查 + 人工 |
| 政治表述准确性 | 15% | 对照知识库范文 |
| 事实真实性（无幻觉） | 20% | 人工核查占位符使用 |

### 2.4 Viewer

评估完成后，启动输出对比视图：

```bash
# （可选）启动本地 Web 查看器，依赖 scripts/eval_viewer.py
python scripts/eval_viewer.py \
  --results-dir "evals-results/iteration-1" \
  --port 8080
```

---

## 三、技能迭代优化

### 3.1 从反馈中提炼改进

- **不要过拟合测试用例** — 变化要通用，不能只对那 3 个例子有效
- **保持 prompt 精简** — 删除不产生价值的指令
- **解释"为什么"** — 告诉 AI 某个要求背后的理由，比 MUST/Never 更有效
- **观察重复劳动** — 如果多个测试的 AI 都写了同样的 helper 脚本，就把它 bundle 到 scripts/

### 3.2 迭代循环

```bash
# 编辑 SKILL.md → 重新运行
python scripts/skill_runner.py \
  --skill-path ".opencode/skills/目标技能" \
  --evals ".opencode/skills/目标技能/evals/evals.json" \
  --output-dir "evals-results/iteration-2"

# 对比两次迭代
python scripts/skill_runner.py --compare \
  --old "evals-results/iteration-1" \
  --new "evals-results/iteration-2"
```

直至以下条件满足其一停止：
- 用户口头确认满意
- 所有测试反馈为空（无改进意见）
- 连续两次迭代无实质性改进

### 3.3 盲评对比（可选）

当需要严格判断新版本是否更好时：
1. 分别运行新版和旧版（或 baseline），产出结果 A 和 B
2. 让一个"评审副本"（不告知哪个是新版）对比评估
3. 记录评审选中新版的次数

---

## 四、Description 优化

### 4.1 生成触发评估查询

创建 20 条查询（10 条应触发、10 条不应触发），重点放边界案例：

```json
[
  {"query": "帮我写一份关于XX的通知", "should_trigger": true},
  {"query": "把这个Excel转成PDF", "should_trigger": false},
  ...
]
```

### 4.2 自动化优化

本项目暂不支持自动优化循环。可手动微调 description 后重复第二节的测试流程验证触发率变化。

---

## 五、与现有技能的配合

| 现有技能 | 与 skill-creator 的关系 |
|---------|----------------------|
| official-document-writing | skill-creator 创建的新技能在此编排 |
| doc-templates | 创建新技能时可参考其模板架构 |
| doc-format | 可用于自动验证格式合规性断言 |
| doc-proofread | 其"校验报告"结构可作评估维度参考 |
| doc-rag | 创建技能时可利用 RAG 检索知识库辅助编写 |
| doc-style | 其质量清单可作语言规范评估标准 |

---

## 六、注意事项

- 本项目的 skills 目录在 `.opencode/skills/` 下，evals 结果输出到项目根目录的 `evals-results/`
- 测试用例中的 prompt 要足够详细、逼真，包含路径、人名、具体场景等上下文
- 不应触发查询要设计为"容易混淆的邻域"（如"帮我校对一下这份报告"——应触发 `doc-proofread` 而不应触发 `skill-creator`）
- 运行测试前确保 `utils/` 目录下的工具可用
