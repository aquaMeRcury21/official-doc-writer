# [单位名称]公文撰写工作站

> **使用前配置**：将本项目中所有 `[单位名称]`、`[地名]`、`[公众号名称]`、`[发文机关简称]` 替换为您的实际信息。
> 搜索范围：`AGENTS.md`、`.opencode/skills/`、`utils/` 中的注释和示例代码。
> API Key：复制 `.env.example` 为 `.env`，填入您的 DeepSeek API Key。

本项目为党政机关公文撰写专用工作区。使用 OpenCode 辅助起草、校对、归档全流程。

## 目录结构

```
├── AGENTS.md                 # 本文件（顶层指南）
├── opencode.json             # OpenCode 配置
├── output/2026/               # 年度产出公文（按类别编号）
│   ├── 0000——个人/           # 每类下按 YYYYMMDD——事项/ 建子目录
│   ├── 0001——[类别名称]/   # _data/ 下放 公文数据.json + 模板.txt
│   └── ...
├── workspace/                  # 临时工作目录
├── knowledge-base/             # 三层知识库（只读）
│   ├── global-knowledge/     # 政策文件、书记讲话范文
│   ├── category-knowledge/   # 按文种分类（工作总结、信息报送）
│   └── archive/              # 历年归档文稿（查重用）
├── utils/                    # Python 工具库（RAG引擎、docx生成、校验、校对）
│   └── templates/            # 各文种参考模板（占位符示例）
├── .opencode/
│   ├── agent/                # 3 个自定义 Agent
│   ├── commands/             # 13 个 slash 命令
│   ├── skills/               # 8 个公文技能（doc-format/doc-proofread/doc-rag/doc-style/doc-templates/official-document-writing/skill-creator/agent-browser）
│   ├── plugins/              # 本地 hooks 插件
│   └── preload-skills.json   # 自动触发规则
```

## 知识库

三层架构，写作前必须检索 `knowledge-base/` 获取范文参考。

- **global-knowledge/**：市委主要领导讲话、上级政策文件
- **category-knowledge/**：按文种分类（工作总结/信息报送等）
- **archive/**：已归档历年产出文稿，用于查重和同期参照

```python
from utils.rag_engine import RAGEngine
rag = RAGEngine()
context = rag.search_as_context(user_query, layer='global', top_k=5)
```

## 常用命令

| 命令 | 用途 |
|------|------|
| `/修改` | **数据驱动起草或修改公文（推荐）**：写新文件同步生成数据+模板；改旧文件读数据→改数据/模板→重新生成 |
| `/通知` | 起草通知 |
| `/请示` | 起草请示 |
| `/报告` | 起草报告 |
| `/函` | 起草函件 |
| `/纪要` | 起草会议纪要 |
| `/总结` | 起草工作总结 |
| `/讲话稿` | 起草领导讲话稿 |
| `/简报` | 起草简报 |
| `/方案` | 起草工作方案 |
| `/校对` | 9 维深度校对 |
| `/归档` | 按规则归档到知识库 |
| `/评估` | 公文质量评估与基准测试 |
| `/kb-update` | 扫描 `kb-inbox/` 目录自动分类入库 |

## Agent 角色

| Agent | 调用方式 | 职责 |
|-------|---------|------|
| writer | `@writer` | 公文撰写全流程 |
| proofreader | `@proofreader` | 9 维深度校对 |
| grader | `@grader` | 质量评估与基准测试 |

## 写作铁律

1. **知识库优先**：动笔前必须检索知识库，模仿范文的排比结构、用词习惯和文风
2. **真实性优先**：不给的事实用 `[待补充]` 占位，绝不瞎编
3. **禁用提法**：已不再使用的旧提法一律禁用，以市委市政府当前正式表述为准
4. **机构简称**：不加"市委、市"前缀（例外：市委办），如统战部、宣传部、发改局
5. **季度查重**：周期性材料与上季度相似度 ≥70% 驳回重写
6. **逐节构建**：先出大纲确认，再逐节撰写，每节确认后再推进
7. **三步输出**：每篇公文同步产生三样东西——结构化数据到 `_data/` → .txt 到知识库 → .docx 到年度目录
8. **数据模板同步**：结构化内容改 `公文数据.json`，措辞润色改 `XX模板.txt`，改完重新生成即可

## 输出路径规则

- 数据与模板 → `output/年份/序号——类别/事项文件夹/_data/公文数据.json`
- 数据与模板 → `output/年份/序号——类别/事项文件夹/_data/XX模板.txt`
- .docx → `output/年份/序号——类别/事项文件夹/YYYYMMDD——标题（HHMM）.docx`
- .txt → `knowledge-base/archive/年份/序号——类别/事项文件夹/YYYYMMDD——标题（HHMM）.txt`
- 同一事项复用现有文件夹，不复建

## 类别编号

| 编号 | 类别 |
|------|------|
| 0000 | 个人 |
| 0001 | 业务工作 |
| 0002 | 综合管理 |
| 0003 | 模板 |
| 0004 | [类别名称] |
| 0005 | [类别名称] |
| 0006 | [类别名称] |
| 0007 | [类别名称] |

## 国家级标准

严格遵循 GB/T 9704-2012《党政机关公文格式》。

层次序号：一、 （一） 1. （1）

- 标题：方正小标宋简体 2号
- 正文：仿宋_GB2312 3号（16pt）
- 行距：固定值 28pt
- 页边距：上3.7cm 下3.5cm 左2.8cm 右2.6cm

## 约束

- **严禁**修改 `knowledge-base/global-knowledge/` 和 `knowledge-base/category-knowledge/` 下的范文文件
- **严禁**在路径中嵌套 `工作/工作/` 目录
- 归档后的 .txt 文件不要手动删改
