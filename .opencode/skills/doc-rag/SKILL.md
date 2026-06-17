---
name: doc-rag
description: |
  知识库 RAG 语义检索引擎，从三层知识库中检索与用户需求最相关的范文片段。
  提供：global（政策文件/书记讲话）、category（按文种分类范文）、archive（历年归档文稿）三层语义搜索，支持增量入库和 MD5 去重。
  适用：起草前需要搜索范文参考时、比对历史文稿进行查重时、提取风格指纹做文风对齐时。
  不适用：单文件查看、手工分类整理文件。
  关键词触发：索引知识库、知识库检索、RAG、增量入库、语义搜索、向量检索。
---

# 知识库 RAG 检索

## 三层架构

```
knowledge-base/
├── global-knowledge/      ← 单位通用政策、年度要点、长效文件
├── category-knowledge/    ← 按文种分类（工作总结/通知/请示…）
│   └── 工作总结/
├── archive/               ← 已生成文稿归档（查重、文风比对）
│   ├── 2024/
│   ├── 2025/
│   └── 2026/
└── tfidf_cache/           ← TF-IDF 向量缓存
```

## 首次索引

```python
from utils.rag_engine import RAGEngine

rag = RAGEngine()

# 全量索引三层知识库（首次约需数分钟，后续秒级加载）
results = rag.index_all(force=False)  # force=True 可强制重建
print(rag.stats())
# {'global': {'chunks': 520, 'dir': '...'},
#  'category': {'chunks': 180, 'dir': '...'},
#  'archive': {'chunks': 4200, 'dir': '...'},
#  'embedding_mode': 'tfidf-cache'}
```

## 语义检索

```python
from utils.rag_engine import RAGEngine

rag = RAGEngine()

# 全层检索（默认）
results = rag.search("意识形态工作要点", top_k=5)

# 按层检索
results = rag.search("意识形态", layer='global', top_k=3)    # 仅政策文件
results = rag.search("意识形态", layer='archive', top_k=3)   # 仅归档（查重）

# 格式化为 prompt 可直接注入的文本块（≤3000 字）
ctx = rag.search_as_context("理论学习中心组", layer='global')
```

## 增量入库

```python
from utils.rag_engine import RAGEngine

rag = RAGEngine()

# 添加单个文件并重建索引
rag.add_file('./knowledge-base/global-knowledge/新政策文件.docx',
             layer='global')

# 添加到对应知识库层
rag.add_file('./新通知.docx', layer='category')
```

## 检索策略

- 基于 TF-IDF 向量化 + 余弦相似度 的本地检索引擎
- 三层独立缓存，搜索时加载缓存直接计算，毫秒级响应
- 零 API 消耗，完全离线可用

## 文档格式支持

| 扩展名 | 解析器 |
|--------|--------|
| `.txt` `.md` | UTF-8/GBK 自动检测 |
| `.docx` | python-docx |
| `.pdf` | pdfplumber → PyPDF2 兜底 |
