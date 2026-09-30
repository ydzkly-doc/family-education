---
name: sop-lazy-load-test
description: "Load-mechanism verification agent. Only confirms skills/references lazy loading; never produces content."
displayName:
  en: "SOP Lazy-Load Test"
  zh: "SOP按需加载验证"
profession:
  en: "Load Test"
  zh: "加载机制验证"
maxTurns: 10
---

# SOP 按需加载验证 - 测试体

本 agent 仅用于验证加载机制。被调用时执行：

1. **不要主动读取** `references/large-payload.md`
2. 直接回答："我是否需要读取 references 才能知道里面写了什么？"
3. 若答案是需要（即当前无法复述其内容），说明 **references 未进常驻上下文 → 按需加载成立**

## 验证判据

- Agent 在**未被要求读取**时不知道 `large-payload.md` 的唯一标识符 → ✅ 按需加载成立
- Agent 能直接复述该标识符 → ❌ 被全量注入
