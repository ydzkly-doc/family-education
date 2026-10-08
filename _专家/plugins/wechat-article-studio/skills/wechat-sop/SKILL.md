---
name: wechat-sop
description: |
  公众号爆款工坊 SOP 执行细则库。承载第 0–12 步的完整执行细则、输出规范与视觉识别标准；
  当执行公众号内容生产的具体步骤（规划、写正文、排版、组装发布包、自检、维护）时，
  按下方「何时加载」表读取对应 references 文件。本文件与 references 均自标准版 SOP 原文搬运。
agent_created: true
---

# 公众号爆款工坊 · 执行细则库

> **本 skill 是「按需参考层」**：细则不常驻上下文，**用到哪一步读哪个文件**。
> 流程骨架、P0 红线、Gate 关卡在专家本体（agent md）中，已常驻，无需在此重复。

## 何时加载（按当前正在执行的步骤查表）

| 何时加载 | 文件 |
|---|---|
| 规划/选题（第 0–1 步） | `references/01-planning.md` |
| 写正文（第 2 步） | `references/02-writing.md` |
| 正文 HTML（第 4 步 + 输出规范） | `references/04-html.md` |
| 卡片/手册/发布包（第 3、5、6、7 步） | `references/05-publish-kit.md` |
| 沉淀与自检（第 8–9 步） | `references/08-selfcheck.md` |
| **卡片文章（贴图）· 总纲**（第 9.5 步，**先读**） | `references/13-card-article.md` |
| 卡片文章 · **内容设计**（拆卡 / 描述 / 标注） | `references/14-card-writing.md` |
| 卡片文章 · **视觉技术**（底图 / 排版引擎 / 渲染断言） | `references/15-card-visual.md` |
| 维护·素材池·数据复盘（第 10–12 步） | `references/10-ops.md` |
| 视觉识别（做封面/配色时） | `references/vision.md` |

## 使用纪律

1. **先看专家本体的流程骨架**判断当前在第几步，**再来这里读对应细则**——不要一次性读完所有文件。
2. 细则与专家本体冲突时，**以专家本体为准**（尤其是 P0 红线与 Gate 关卡）。
3. 本库**只增补执行细节**，不改变"三档优先级"的裁决顺序。
