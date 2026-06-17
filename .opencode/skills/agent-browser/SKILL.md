---
name: agent-browser
description: |
  Browser automation CLI for AI agents. Controls Chromium via CDP protocol.
  Provides: page navigation, form filling, clicking, screenshots, data extraction, Web app testing, Electron app automation.
  适用：搜索网上政策文件时、查阅[公众号名称]获取最新官方表述时、从网页抓取参考资料时。
  不适用：纯文本处理、本地文件读写。
  关键词触发：浏览器、搜索网页、截图、填表、网页自动化、获取数据。
allowed-tools: Bash(agent-browser:*)
---

# agent-browser

Fast browser automation CLI for AI agents. Chrome/Chromium via CDP with accessibility-tree snapshots and compact `@eN` element refs.

已在当前环境全局安装（`%USERPROFILE%\.agent-browser\bin\agent-browser.exe` 已在 PATH 中）。

## 使用方式

直接运行 `agent-browser` 命令即可，例如：

```bash
agent-browser open <url>
agent-browser snapshot
agent-browser click @e1
```

详细用法请运行以下命令获取与当前版本匹配的完整指南：

```bash
agent-browser skills get core
```

## 工作流程

1. **打开浏览器**: `agent-browser open <url>`
2. **获取页面快照**: `agent-browser snapshot`（返回无障碍树 + `@eN` 元素引用）
3. **与元素交互**: `agent-browser click @e1` / `agent-browser fill @e2 "text"`
4. **截图**: `agent-browser screenshot page.png`
5. **关闭**: `agent-browser close`

## 常用命令速查

- `agent-browser open <url>` — 打开页面
- `agent-browser click <sel>` — 点击元素
- `agent-browser fill <sel> <text>` — 填写输入框
- `agent-browser type <sel> <text>` — 键入文本
- `agent-browser snapshot` — 无障碍树快照
- `agent-browser screenshot [path]` — 截图
- `agent-browser get text <sel>` — 获取文本
- `agent-browser get url` — 获取当前 URL
- `agent-browser eval <js>` — 执行 JavaScript
- `agent-browser close` — 关闭浏览器
