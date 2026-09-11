# 迁移来源与适用边界

- 迁移日期：2026-09-10。
- 用户指定来源：`D:/个人资料/家庭教育/_专家/wechat-article-studio.zip` 内 `wechat-article-studio/agents/wechat-article-studio.md`，标题“公众号爆款工坊 - 公众号内容流水线”。
- 原始 ZIP 保留。Codex 版不包含另一份 video-script-studio 专家，不安装 CodeBuddy 插件或替换原平台专家。
- 本版以短入口与分主题参考文件承载同一工作流；采用 Codex 的 SKILL.md 与 agents/openai.yaml 格式。
- 保留课程／读书笔记／原创经历分型、父亲叙事、三道确认、预览隔离、严格／legacy 检查及清理机制。发布包件数以标准版为准：**2026-09-10 起为三件套**（正文 + 01 字段表 + 封面），02 操作指南停止生成新篇、存量保留。
- 消除源文件内部旧 table／680px 骨架与新 section 规范冲突；以较新的带篇号命名、txt 指南、独立 _预览 目录为准。
- 不移植 displayName/profession/maxTurns 等 CodeBuddy 专用元数据、present_files、注册命令和私有 Python 路径。
- 三道人工关卡按标准版执行：只认上一阶段成果出现后、用户当次明确点名下一步的确认；不承认概括式跨阶段授权。减少预览与交付不等于减少确认。
- 不将源文关于微信账号 API 权限、积分收费、平台条款或特定客户端机理的历史判断写成当前确定事实。需要回答这些问题时重新核验。
- 不复用固定去水印坐标；图像生成和编辑服从当前工具规则。
- 课程个案与半虚构叙事不得宣称为用户真实经历；来源声明不是事实校验的替代。

此文件用于追溯迁移选择，执行流程以 SKILL.md 及其专题参考文件为准。

## 两版同步规则（2026-09-10 用户确立）

WorkBuddy 专家版（`_专家/wechat-article-studio.zip` / `agents/wechat-article-studio.md`）是**标准版**；本 Codex 版是**派生版**。改动标准版时按以下规则同步，避免两版越走越远：

**必须同步（内容标准，与平台无关）** —— 改标准版时**同一轮内**同步到本版对应 references：

| 内容标准 | 本版落地位置 |
| --- | --- |
| 叙事真实性三分法与人物连续性 | `references/quality.md` §一 |
| 五层完整性、30% 降幅复核线、篇幅区间 | `references/quality.md` §七 |
| 去模板化、结构轮换、语言指纹、相邻篇轮换 | `references/quality.md` §二、`references/editorial.md` |
| 标题三类轮换、备选标题须有据 | `references/quality.md` §三、`references/editorial.md` |
| 事实核验分级、适用与风险边界 | `references/quality.md` §四 |
| 系列规模与跨系列处理 | `references/editorial.md` |
| 发布包件数与卫生、微信正文规范、封面比例与安全区 | `references/publishing.md` |
| 巡检分类、清理安全流程 | `references/maintenance.md` |
| 工具脚本的参数与用途 | `references/publishing.md` |

**不同步（平台适配层）** —— 两版本就该不同，不互相抄：

- `present_files`、专家注册命令、CodeBuddy 专用元数据（displayName / profession / maxTurns）；
- WorkBuddy 私有 Python 解释器绝对路径（本版按当前工作区运行时定位）；
- 生图积分提示、绑死某一平台的固定裁切坐标与去水印命令（本版服从当前图像工具规则）；
- `agents/openai.yaml` 等 Codex 格式文件。

**冲突时**：以标准版为准，并在本文件记录差异原因（例如本版曾把发布包写成四件套、把水印写成"不自动去除"，均已按标准版修正）。
