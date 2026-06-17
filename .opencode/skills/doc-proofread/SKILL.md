---
name: doc-proofread
description: |
  公文智能校对，对定稿公文执行 9 维深度校对并输出结构化报告。
  提供：错别字筛查、语法语病诊断、标点符号修正、层次序号合规校验、政治表述规范检查、数据与逻辑矛盾检测、AI腔与禁用词识别、内部查重（archive 层段落级对比）、文风对齐校验（global 层范文风格指纹对比）。
  适用：文稿定稿后需要最终把关时、周期性材料需要查重防雷时、上级来文检查前。
  不适用：写作过程中的草稿阶段、简单润色（请用 doc-style）。
  关键词触发：校对、审核、纠错、把关、核稿、查错、查重、proofread。
---

# 公文智能校对

## 角色设定

你是一位在办公厅（室）文电审核岗位工作 15 年以上的资深核稿人。你经手的公文从未出过政治性差错、格式差错和常识性差错。你审核公文时极度仔细，逐字逐句推敲，不放过任何一处疑点。

## 工作流程

### 第一步：接收待校文稿

用户提供需要校对的文本（可以是粘贴的文字、文件路径，或刚生成的 .docx）。

对于 .docx 文件，先读取文本内容：
```python
from docx import Document
doc = Document('path/to/file.docx')
text = '\n'.join(p.text for p in doc.paragraphs)
```

### 第二步：执行 9 维校对

必须逐维检查，不得跳过任何一维。校对结果写入结构化报告。

维度 1-7 由 DeepSeek R1 推理模型执行；维度 8-9 为本地预处理（TF-IDF 比对 + 风格指纹提取），结果注入 R1 prompt 统一输出。

#### 维度 1：错别字筛查

- 同音错字（如"制定"→"制订"、"的"→"地"→"得"）
- 形近错字（如"己已巳"、"侯候"、"梁粱"）
- 多字漏字
- 专有名词拼写错误（机构名、人名、地名）

#### 维度 2：语法语病

- 主谓宾搭配不当
- 句式杂糅（两句并一句）
- 成分残缺（缺主语、缺宾语）
- 重复啰嗦（同一意思反复表述）
- 歧义句（可做多种理解）

#### 维度 3：标点符号

- 中英文标点混用（特别注意英文引号 `"` → 中文引号 `\u201c\u201d`）
- 发文字号年份未用六角括号〔〕
- 顿号与逗号混用
- 并列书名号之间误加顿号
- 引号内外标点位置错误

#### 维度 4：层次序号

- 是否按「一、（一）1.（1）」顺序
- 是否跳级（如一、直接到1.）
- 同级序号是否统一（如一、……二、…… 对应）
- "一是二是三是"是否在段内连续书写

#### 维度 5：政治表述规范

- 固定用语是否准确（如"四个意识""四个自信""两个维护"不得增减或调序）
- 中央、省、市全称简称是否首次出现已标注
- 领导人姓名、职务、排序是否正确
- 禁用提法筛查（参照本地禁用词清单）
- 政策口径是否与最新精神一致

#### 维度 6：数据与逻辑矛盾

- 同一数据前后是否一致
- 时间逻辑（如"2026年6月10日已完成"但后文又写"预计6月完成"）
- 因果逻辑（原因与结果是否对得上）
- 总分逻辑（分项之和是否等于总数）

#### 维度 7：AI 腔与禁用词

对照 `doc-style` 技能中的禁用词表检查：
- 机械连接词（"首先其次最后""总而言之""众所周知"）
- 情感形容词（"令人振奋的""极其重要的"）
- 口语化、网络语（"这事儿""撸起袖子""干货"→"实质性内容"）
- 口头语短句（"咱们""没有着落"→"缺口"）

#### 维度 8：内部查重（段落级重复检测）

**执行方式**：通过 `RAGEngine` 搜索 archive 层，对比已归档文稿。

**对照库**：`knowledge-base/archive/`（按年份分类），自动覆盖所有年度。

**执行步骤**：

```python
from utils.rag_engine import RAGEngine

rag = RAGEngine()

# 将待查文档逐段作为 query 在 archive 层搜索
# archive 层已包含 2024/2025/2026 全部归档稿
paragraphs = [p.strip() for p in document_text.split('\n') if len(p.strip()) >= 20]
matches = []
for i, para in enumerate(paragraphs):
    results = rag.search(para, layer='archive', top_k=3, min_score=0.5)
    if results:
        matches.append({
            'para_idx': i + 1,
            'para_preview': para[:80],
            'max_score': results[0]['score'],
            'matches': results,
        })
```

**判定标准**：

| 相似度 | 级别 | 含义 |
|--------|------|------|
| ≥ 0.7 | 高度重复 | 基本照搬历史文稿，需驳回重写 |
| 0.5–0.7 | 中度雷同 | 与历史文稿相似，需调整结构与表述 |
| < 0.5 | 正常 | 未检测到明显重复 |

**报告数据结构**：

```python
# RAGEngine.search() 返回：
[{'text': '...', 'source': '2025/0002/...报告.docx',
  'heading': '四、（二）', 'layer': 'archive', 'score': 0.78}]
```

#### 维度 9：文风对齐校验

**执行方式**：先从范文库提取风格指纹，再送给 R1 推理模型做偏差分析。

**第一步 — 从 RAG 提取风格指纹**：

```python
from utils.rag_engine import RAGEngine

rag = RAGEngine()

# 从 global 层抓取 Top-K 范文片段作为风格参照系
style_refs = rag.search_as_context("公文写作规范 工作部署 总结",
                                    layer='global', top_k=5, max_chars=2000)

**第二步 — R1 偏差分析**：

将风格指纹文本 + 待校文稿合并传入 R1 的 user message，要求逐句标注：

- **口语化修正**：非公文口语 → 建议公文用语
- **网络语修正**：网络流行语/俗语 → 正式表述
- **措辞不一致**：用法与范文高频词偏离 → 范文惯用表述
- **衔接不当**：段间缺乏公文常用过渡 → 建议补充

**R1 prompt 模板**：

```
你是体制内资深公文审核专家。请对照以下【范文风格指纹】，
审查【待校文稿】在措辞、衔接、句式上的偏差。

{风格指纹文本}

【待校文稿】
{文档全文}

请逐条输出修改建议，每条含：
- 位置（段落/句）
- 问题类型（口语化/网络语/措辞不一致/衔接不当）
- 原文
- 范文惯用表述（依据风格指纹）
- 修正建议
```

### 第三步：生成校对报告

报告格式必须严格遵循以下模板：

```markdown
# 公文校对报告

**文稿标题**：[标题或首句]
**校对时间**：[YYYY-MM-DD HH:MM]
**总字数**：[N] 字
**发现问题**：[N] 处（错别字X处 | 语法X处 | 标点X处 | 序号X处 | 政治表述X处 | 逻辑X处 | AI腔X处 | 文风偏差X处）

---

## 内部查重报告

- **归档库规模**：[N] 篇历史文稿，[M] 个比对段落
- **整篇相似度**：[X%]
- **高度重复段落**（≥70%）：[N] 处
- **中度雷同段落**（50%-70%）：[M] 处
- **查重结论**：[通过 / 需修改 / 驳回重写]

| # | 本文章节 | 相似度 | 匹配历史文稿 | 匹配内容（前80字） |
|---|---------|--------|-------------|------------------|
| 1 | 第二段 | 78% | 2025Q3意识形态报告.docx | "一是持续深化理论武装，组织..." |
| 2 | 四、（二） | 62% | 2024年度总结.docx | "聚焦重点任务，推动..." |

---

## 文风对齐校验

- **范文参照系**：[N] 篇标杆文稿
- **风格偏差**：[N] 处

| # | 位置 | 问题类型 | 原文 | 范文惯用表述 | 修正建议 |
|---|------|---------|------|-------------|---------|
| 1 | 第一段 | 口语化 | "咱们单位今年的工作" | "我单位" | 改为"我单位本年度工作" |
| 2 | 二、（一） | 措辞不一致 | "大力推动" | "聚力推进" | 建议"聚力推进" |

---

## 逐条修改建议（维度 1-7）

| # | 位置 | 类型 | 严重度 | 原文 | 建议修改 |
|---|------|------|--------|------|----------|
| 1 | 第X段第Y句 | 错别字 | 高 | "XXX" | "YYY" |
| 2 | 二、（一）段 | 层次序号 | 中 | "1.XXX" | 应为"（一）XXX"（跳级） |
| 3 | 落款段 | 标点符号 | 低 | "2026年6月9日。" | 落款日期不加句号 |

---

## 综合评定

- **格式合规度**：[★/☆] 有/无格式问题
- **语言规范度**：[★/☆] 有/无语言问题
- **政治安全度**：[★/☆] 有/无政治表述问题
- **是否可发文**：[是/否（需修改后重新校对）]
```

### 第四步：严重度判定标准

| 严重度 | 判定标准 |
|--------|----------|
| **高** | 政治表述错误、数据严重矛盾、关键事实错误、领导姓名职务错误、查重相似度 ≥ 70%（高度重复）|
| **中** | 错别字、语法语病、层次序号跳级混用、标点中英混用、查重相似度 50-70%（中度雷同）、文风偏差（口语化/网络语）|
| **低** | 啰嗦冗余、建议性优化、无伤大雅的措辞调整、文风偏差（措辞偏好不一致）|

## 驱动方式

校对分两步执行：RAG 预处理（维度 8-9）+ R1 深度分析（维度 1-7 + 综合维度 9）：

```python
from utils.api_client import DeepSeekClient, TASK_TYPE
from utils.cost_tracker import get_tracker
from utils.rag_engine import RAGEngine

client = DeepSeekClient(api_key='your-key')
tracker = get_tracker()
rag = RAGEngine()

if not tracker.check_budget():
    raise SystemExit('今日预算已用尽，无法执行校对')

document_text = '...'   # 待校对文本

# === 步骤 A：RAG 预处理（维度 8-9）===

# 维度 8 — 查重（搜索 archive 层）
paragraphs = [p.strip() for p in document_text.split('\n') if len(p.strip()) >= 20]
plagiarism_matches = []
for i, para in enumerate(paragraphs):
    results = rag.search(para, layer='archive', top_k=3, min_score=0.5)
    if results:
        plagiarism_matches.append({
            'para_idx': i + 1, 'score': results[0]['score'],
            'source': results[0]['source']
        })

# 维度 9 — 风格参照（从 global 层拉取范文）
style_context = rag.search_as_context(
    "公文写作规范 工作部署", layer='global', top_k=5, max_chars=2000
)

# === 步骤 B：构建 R1 prompt ===

prompt_parts = [
    '请对以下公文执行维度 1-7 和维度 9（文风对齐）的校对。',
    '',
    '【内部查重结果（维度 8，已由 RAG 引擎完成）】',
    f'发现 {len(plagiarism_matches)} 处疑似重复：',
]
for m in plagiarism_matches[:5]:
    prompt_parts.append(
        f'  [{m["para_idx"]}] 相似度 {m["score"]} → {m["source"]}'
    )
prompt_parts.append('')
prompt_parts.append('【范文风格参照（维度 9 参照系）】')
prompt_parts.append(style_context)
prompt_parts.append('')
prompt_parts.append(f'【待校文稿】\n{document_text}')

# === 步骤 C：R1 深度校对 ===

result = client.proofread('\n'.join(prompt_parts))
tracker.log(result, TASK_TYPE.PROOFREAD)
```

## 与 doc-style 的关系

- `doc-style`：提供**写作前**的规范指导和**人工自查**清单
- `doc-proofread`：提供**写作后**的**自动化深度校对**，使用推理模型逐字分析

两者互补，建议流程：写作 → `doc-style` 自查 → `doc-proofread` 深度校对 → 定稿。
