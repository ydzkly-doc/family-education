---
name: skill-bundle-test
description: |
  加载机制验证用最小 skill。仅用于确认 SKILL.md + references/ 结构能否被平台识别与按需加载，
  不参与任何实际内容生产。当用户提到"小样验证""加载机制验证"时使用。
agent_created: true
---

# skill-bundle-test

本 skill 是**结构验证小样**，用于确认 `SKILL.md + references/` 的按需加载机制在本地专家包中可用。

## 验证点

1. SKILL.md 本体小（应常驻上下文）
2. `references/` 内文件大（应**按需**读取、非常驻）
3. 平台能识别 skill 目录并被 plugin.json 的 `skills` 字段引用

## 按需读取表（模拟正式拆分的形态）

| 何时加载 | 文件 | 说明 |
|---|---|---|
| 需要测试大文件加载行为时 | `references/large-payload.md` | 模拟"执行细则层"（正式版这里放第 2/4/7/9 步细则） |
| 需要测试二级引用时 | `references/nested-detail.md` | 模拟"踩坑示例层" |

**执行方式**：命中条件时用 Read 工具读取对应文件；未命中则不读（这正是要验证的行为）。
