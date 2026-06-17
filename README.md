# official-doc-writer

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](pyproject.toml)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Release](https://img.shields.io/github/v/release/aquaMeRcury21/official-doc-writer)](https://github.com/aquaMeRcury21/official-doc-writer/releases)

**⬇️ [下载 v0.2.0 便携版 exe](https://github.com/aquaMeRcury21/official-doc-writer/releases/tag/v0.2.0) （Windows 单文件，双击即用）**

</div>

AI 辅助党政公文撰写工作台。提供 PyQt6 桌面端 + OpenCode CLI 两种使用方式，严格遵循 **GB/T 9704-2012《党政机关公文格式》** 国家标准。

## GUI 桌面版（推荐）

[下载 `公文撰写工作站.exe`](https://github.com/aquaMeRcury21/official-doc-writer/releases/tag/v0.2.0) → 双击运行 → 设置页填入 API Key → 立即使用。

| 面板 | 功能 |
|------|------|
| **起草** | 选文种 → 写需求 → AI 生成 → 编辑 → 导出 .docx（自动更新知识库索引） |
| **校对** | 粘贴全文 → AI 9 维深度校对 → 格式化报告输出 |
| **知识库** | 三层语义检索（global / category / archive），一键重建索引 |
| **归档** | 浏览归档文件，批量扫描入库 |
| **设置** | 单位信息、API Key、日预算，保存即生效 |

首次启动自动解压知识库，无需手动配置。

## 核心功能

- **AI 智能起草** — 支持通知、请示、报告、讲话稿、简报、方案、纪要、函、工作总结等 9 种常用文种
- **国标格式输出** — 自动生成符合 GB/T 9704-2012 的 `.docx` 文件（页边距、字体字号、行距、层次序号全自动）
- **9 维深度校对** — 错别字、语法语病、标点符号、层次序号、政治表述、数据逻辑矛盾、AI 腔与禁用词、内部查重、文风对齐
- **RAG 知识库检索** — 三层 TF-IDF 语义搜索（政策文件 / 分类范文 / 历年归档），动笔前自动匹配参考范文
- **API 费用管控** — DeepSeek 调用日志记录 + 日预算上限，防止超额
- **AI 腔清除** — 内置语料库和检查规则，自动识别并修正 LLM 常见套路化表达

## 开发者：从源码运行

```bash
# 1. 克隆项目
git clone https://github.com/aquaMeRcury21/official-doc-writer.git
cd official-doc-writer

# 2. 安装依赖
pip install -e .

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key

# 4. 索引知识库
python -c "from utils.rag_engine import RAGEngine; RAGEngine().index_all()"

# 5. 启动 GUI
python gui/main.py
```

## 配合 OpenCode 使用

本项目也可与 [OpenCode](https://opencode.ai)（AI 编程助手）配合使用。

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
├── gui/                        PyQt6 桌面端
│   ├── main.py                 入口
│   ├── backend.py              后端封装（路径/API 客户端）
│   ├── main_window.py          主窗口（侧边栏导航 + 页面栈）
│   ├── widgets/                5 个功能面板
│   └── resources/styles.qss    界面样式表
├── utils/                      Python 工具库
│   ├── api_client.py           DeepSeek API 客户端（重试/计费/模型路由）
│   ├── rag_engine.py           TF-IDF 语义检索引擎
│   ├── document_generator.py   GB/T 9704-2012 格式 .docx 生成器
│   ├── document_parser.py      多格式文档解析器（txt/docx/pdf/xlsx）
│   ├── cost_tracker.py         API 费用跟踪与预算控制
│   ├── settings.py             全局配置（路径、组织名称等）
│   └── templates/              9 种公文文种参考模板
├── .opencode/                  OpenCode 技能、命令、Agent 配置
├── knowledge-base/             三层知识库
├── output/                     年度产出目录
├── workspace/                  临时工作目录
├── tests/                      单元测试
└── docs/                       文档
```

## 知识库架构

三层设计，动笔前自动检索：

| 层级 | 内容 | 用途 |
|------|------|------|
| `global-knowledge/` | 上级政策文件、讲话范文 | 权威表述与政治术语参照 |
| `category-knowledge/` | 按文种分类的范文 | 结构与文风模仿 |
| `archive/` | 历年已归档产出文稿 | 查重与同期对比 |

```python
from utils.rag_engine import RAGEngine
rag = RAGEngine()
context = rag.search_as_context('工作', layer='global', top_k=5)
```

## 公文格式标准（GB/T 9704-2012）

| 项目 | 参数 | 实测 |
|------|------|------|
| 页面 | 21.0 × 29.7 cm | OK |
| 上边距 | 3.7 cm | OK |
| 下边距 | 3.5 cm | OK |
| 左边距 | 2.8 cm | OK |
| 右边距 | 2.6 cm | OK |
| 标题 | 方正小标宋简体 2号（22pt） | OK |
| 正文 | 仿宋_GB2312 3号（16pt） | OK |
| 行距 | 固定值 28pt | OK |
| 引号 | 全角弯引号 | OK |
| 层次序号 | 一、 （一） 1. （1） | |

## 系统要求

**GUI 桌面版：** Windows 10/11（无需 Python）

**源码运行：** Python 3.13+

**通用：** DeepSeek API Key（[申请地址](https://platform.deepseek.com)）

## 技术栈

| 组件 | 用途 |
|------|------|
| Python 3.13 | 运行时 |
| PyQt6 | 桌面 GUI |
| scikit-learn | TF-IDF 语义检索（RAG 引擎） |
| python-docx | 公文格式 .docx 生成 |
| PyInstaller | 单文件 exe 打包 |

## 贡献指南

欢迎提交 Issue 和 Pull Request，请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
