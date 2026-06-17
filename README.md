# official-doc-writer

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](pyproject.toml)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/your-username/official-doc-writer/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/official-doc-writer/actions/workflows/ci.yml)

</div>

AI 辅助党政公文撰写工作台

基于 [OpenCode](https://opencode.ai) 构建，提供从起草、校对、评估到归档的全流程公文写作支持，严格遵循 **GB/T 9704-2012《党政机关公文格式》** 国家标准。

## 核心功能

- **AI 智能起草** — 支持通知、请示、报告、讲话稿、简报、方案、纪要、函、工作总结等 9 种常用文种
- **国标格式输出** — 自动生成符合 GB/T 9704-2012 的 `.docx` 文件（页边距、字体字号、行距、层次序号全自动）
- **9 维深度校对** — 错别字、语法语病、标点符号、层次序号、政治表述、数据逻辑矛盾、AI 腔与禁用词、内部查重、文风对齐
- **RAG 知识库检索** — 三层 TF-IDF 语义搜索（政策文件 / 分类范文 / 历年归档），动笔前自动匹配参考范文
- **API 费用管控** — DeepSeek 调用日志记录 + 日预算上限，防止超额
- **AI 腔清除** — 内置语料库和检查规则，自动识别并修正 LLM 常见套路化表达

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/your-username/official-doc-writer.git
cd official-doc-writer

# 2. 安装依赖
pip install -e .

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key

# 4. 索引知识库
python -c "from utils.rag_engine import RAGEngine; RAGEngine().index_all()"
```

## 配合 OpenCode 使用

本项目设计为与 [OpenCode](https://opencode.ai)（AI 编程助手）配合使用。

```bash
# 安装 OpenCode
npm install -g @opencode-ai/cli

# 在项目目录启动
opencode
```

启动后自动加载以下斜杠命令：

| 命令 | 用途 |
|------|------|
| `/通知` | 起草通知 |
| `/请示` | 起草请示 |
| `/报告` | 起草报告 |
| `/讲话稿` | 起草领导讲话稿 |
| `/总结` | 起草工作总结 |
| `/简报` | 起草简报 |
| `/方案` | 起草工作方案 |
| `/函` | 起草函件 |
| `/纪要` | 起草会议纪要 |
| `/修改` | 数据驱动修改已有公文 |
| `/校对` | 9 维深度校对 |
| `/归档` | 归档到知识库 |
| `/评估` | 公文质量评估与基准测试 |
| `/kb-update` | 批量扫描入库 |

系统还内置了 3 个 AI Agent：

| Agent | 调用方式 | 职责 |
|-------|---------|------|
| writer | `@writer` | 公文撰写全流程 |
| proofreader | `@proofreader` | 9 维深度校对 |
| grader | `@grader` | 质量评估与基准测试 |

## Python API 示例

```python
from utils.rag_engine import RAGEngine
from utils.document_generator import write_docx
from utils.api_client import DeepSeekClient

# 搜索知识库范文
rag = RAGEngine()
results = rag.search('理论学习', layer='global', top_k=5)
for r in results:
    print(f"[相关度 {r['score']}] {r['source']}")

# 生成标准格式公文
write_docx(
    title='关于开展理论学习活动的通知',
    body=[
        '现将有关事项通知如下：',
        '一、提高思想认识',
        '二、明确学习内容',
        '三、精心组织实施',
    ],
    doc_number='〔2026〕15号',
)

# 调用 DeepSeek API
client = DeepSeekClient.from_env()
result = client.draft('写一份关于安全生产检查的通知')
print(result.content)
```

## 项目结构

```
├── AGENTS.md                    OpenCode AI 助手指令（面向 AI）
├── opencode.json                OpenCode 工作区配置
├── utils/                       Python 工具库
│   ├── api_client.py            DeepSeek API 客户端（重试/计费/模型路由）
│   ├── rag_engine.py            TF-IDF 语义检索引擎
│   ├── document_generator.py    GB/T 9704-2012 格式 .docx 生成器
│   ├── document_parser.py       多格式文档解析器（txt/docx/pdf/xlsx）
│   ├── cost_tracker.py          API 费用跟踪与预算控制
│   ├── settings.py              全局配置（路径、组织名称等）
│   └── templates/               9 种公文文种参考模板
├── .opencode/                   OpenCode 技能、命令、Agent 配置
│   ├── skills/                  8 个专业技能（格式/校对/RAG/文种模板等）
│   ├── commands/                14 个斜杠命令
│   └── agent/                   3 个自定义 Agent
├── knowledge-base/              三层知识库（仅保留目录结构）
├── output/                       年度产出目录（仅保留目录结构）
├── workspace/                    临时工作目录
├── tests/                       单元测试
└── docs/                        文档
```

## 知识库架构

三层设计，动笔前自动检索：

| 层级 | 内容 | 用途 |
|------|------|------|
| `global-knowledge/` | 上级政策文件、书记讲话范文 | 权威表述与政治术语参照 |
| `category-knowledge/` | 按文种分类的范文 | 结构与文风模仿 |
| `archive/` | 历年已归档产出文稿 | 查重与同期对比 |

```python
from utils.rag_engine import RAGEngine
rag = RAGEngine()
context = rag.search_as_context('意识形态工作', layer='global', top_k=5)
```

## 公文格式标准

严格遵循 **GB/T 9704-2012**：

| 项目 | 参数 |
|------|------|
| 标题 | 方正小标宋简体 2号（22pt） |
| 正文 | 仿宋_GB2312 3号（16pt） |
| 行距 | 固定值 28pt |
| 页边距 | 上 3.7cm 下 3.5cm 左 2.8cm 右 2.6cm |
| 层次序号 | 一、 （一） 1. （1） |

## 系统要求

- Python 3.13+
- DeepSeek API Key（[申请地址](https://platform.deepseek.com)）
- 推荐配合 OpenCode 使用

## 贡献指南

欢迎提交 Issue 和 Pull Request，请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
