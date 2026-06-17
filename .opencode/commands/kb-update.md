---
name: kb-update
description: 扫描 kb-inbox 目录，自动分类入库到三层 knowledge-base 并重建索引。
---

请执行以下操作：

1. 运行 Python 脚本：
   ```
   python utils/knowledge_base_updater.py
   ```

2. 向用户汇报处理结果，包括：
   - 处理了多少文件
   - 删除了多少原文件
   - 跳过了多少文件
   - 分别归入了哪些 knowledge-base 层
   - 是否成功重建 RAG 索引
