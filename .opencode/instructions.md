# 项目说明

本项目为公文撰写专用工作区。

## 知识库位置

- 知识库（范文、规范文件）：`./knowledge-base/`
- 写作时优先检索此目录，模仿其中段落的排比结构、用词习惯和文风

## 常用命令

- 起草公文：直接描述需求，如"帮我起草一份关于XX的请示"
- 格式检查：描述已有公文，"检查这份通知的格式是否合规"
- 润色修改：提供初稿，"帮我把这段话改成公文语气"

## 输出路径规则

- 输出 .docx 和 .txt 归档时，优先检查 `output/年份/序号——类别/` 下是否已有同一事项的文件夹
- 若已存在相关文件夹（如同一活动已有通知、主持词等），将新文件放入该文件夹，不复建新文件夹
- 若为全新事项，按 `YYYYMMDD——标题/` 新建文件夹
- .docx 放在 `output/年份/序号——类别/事项文件夹/`，.txt 同步放入 `knowledge-base/archive/年份/序号——类别/事项文件夹/`
- 知识库仅保留 .txt 文件，不保留 .docx
- **严禁在路径中再嵌套一层 `工作/` 目录**，工作区根目录就是 `工作`

## 环境配置

### Python 环境

- Python 3.13+ 已安装（请根据您的实际安装路径配置）
- 所有依赖包已安装（`pip install -r requirements.txt`）
- 关键包：python-docx, scikit-learn, numpy, requests, python-dotenv
- DeepSeek API Key 已配置在 `.env` 文件

### 已知问题

- 系统默认 `python` 命令解析到 Microsoft Store 存根（已重命名为 `python.exe.store` 以规避）
- 若重新打开终端后 `python` 不可用，执行：
  ```powershell
  $env:Path = "[您的Python安装路径];[您的Python安装路径]\Scripts;$env:Path"
  ```
- 或在系统设置中搜索"管理应用执行别名"，关闭 Python 的别名开关

## 技能说明

本工作区包含一个公文撰写专用技能（`official-document-writing`），严格遵循 GB/T 9704-2012 国家标准。
