# 加载机制小样验证

目的：验证 agent 型专家的 `skills` 预加载后，其 `references/` 是否**按需读取**（不进常驻上下文）。

## 实证依据（已从官方插件确认，无需造轮子）

| 证据 | 出处 | 结论 |
|---|---|---|
| `references/ - Documentation intended to be loaded into context **as needed**` | `skill-creator/SKILL.md` L40 | references **按需**加载 |
| `Benefits: Keeps SKILL.md lean, **loaded only when CodeBuddy determines it's needed**` | 同上 L66 | 不进常驻上下文 |
| `keep ... SKILL.md lean while making information discoverable **without hogging the context window**` | 同上 L66 | 明确省上下文 |
| `| 优先级 | 何时加载 | 文件 |` 表 | `tencent-docx/skills/tdoc-orchestrator/SKILL.md` L22 | 官方插件**实际按条件读** |
| `references/ ... 运行时无需加载` | `tencent-docx/skills/html-review/SKILL.md` L43 | 官方明确声明运行时**不加载** |
| `"skills": "./skills"` + `"agents": [...]` 并存 | `tencent-docx/plugin.json` | **agent + skills 可并存** |

## 结论

**方案 A 的机制已确认成立**，且有官方插件实证。本小样仅做最后的**结构可行性验证**（我们的包按此改造后能否正常加载）。
