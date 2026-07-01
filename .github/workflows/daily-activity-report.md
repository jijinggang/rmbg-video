---
emoji: 📊
description: 检查仓库近期 git 活动，生成每日报告并发布为 GitHub Issue
on:
  schedule: daily
  workflow_dispatch:
permissions:
  contents: read
  issues: read
  pull-requests: read
strict: true
network:
  allowed: [defaults, github]
tools:
  github:
    mode: gh-proxy
    toolsets: [default]
safe-outputs:
  mentions: false
  allowed-github-references: []
  create-issue:
    title-prefix: "📊 每日活动报告:"
    labels: [report, daily-activity]
    close-older-issues: true
    expires: 30
---

# 每日活动报告

## Task

检查本仓库过去 24 小时的 git 活动，如果有新 commit 则生成结构化报告并发布为 Issue；无活动时调用 `noop` 跳过。

## 报告窗口

`last 24 full hours ending at workflow start (UTC)`

## 执行步骤

### 1. 获取仓库信息

运行 `gh repo view --json name,owner,defaultBranch` 获取仓库元数据。

### 2. 查询近期活动

```bash
# 获取过去24小时的commit
git log --since="24 hours ago" --format="%H|%ad|%an|%s" --date=short --no-merges

# 统计贡献者
git log --since="24 hours ago" --format="%an" --no-merges | sort | uniq -c | sort -rn

# 统计变更文件
git diff --stat HEAD@{"24 hours ago"}..HEAD 2>/dev/null || git log --since="24 hours ago" --oneline --name-only --no-merges | sort | uniq | head -30
```

### 3. 判断并行动

- **有 commit**: 为每个 commit 获取变更文件详情，生成报告，通过 `create-issue` 发布
- **无 commit**: 调用 `noop("过去24小时无任何commit活动 (窗口: {{window_start}} 至 {{window_end}} UTC)")`

## 报告格式

使用 GitHub-flavored markdown，报告结构如下：

### 概览

| 指标 | 数值 |
|------|------|
| 24h Commit 数 | N |
| 贡献者数 | N |
| 变更文件数 | N |

### 贡献者

列出每位贡献者及其 commit 数。

### Commit 详情

每个 commit 包含：hash（短格式）、作者、日期、描述。

<details>
<summary>查看变更文件</summary>

变更文件列表放在可折叠区域中。

</details>

### 参考链接

链接到仓库的 commits 页面。

## Safe Outputs

- **有活动**: 使用 `create-issue` 发布报告
- **无活动**: 使用 `noop` 明确跳过