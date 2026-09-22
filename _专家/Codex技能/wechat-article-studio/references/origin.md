# 迁移来源与适用边界

- 迁移日期：2026-09-10。
- 用户指定来源：`D:/个人资料/家庭教育/_专家/wechat-article-studio.zip` 内 `wechat-article-studio/agents/wechat-article-studio.md`，标题“公众号爆款工坊 - 公众号内容流水线”。
- 原始 ZIP 保留。Codex 版不包含另一份 video-script-studio 专家，不安装 CodeBuddy 插件或替换原平台专家。
- 本版以短入口与分主题参考文件承载同一工作流；采用 Codex 的 SKILL.md 与 agents/openai.yaml 格式。
- 保留课程／读书笔记／原创经历分型、父亲叙事、长文三道确认及可选卡片文章两道确认、预览隔离、严格／legacy 检查及清理机制。长图文发布包件数以标准版为准：**2026-09-10 起为三件套**（正文 + 01 字段表 + 封面），02 操作指南停止生成新篇、存量保留。
- 消除源文件内部旧 table／680px 骨架与新 section 规范冲突；以较新的带篇号命名、txt 指南、独立 _预览 目录为准。
- 不移植 displayName/profession/maxTurns 等 CodeBuddy 专用元数据、present_files、注册命令和私有 Python 路径。
- 人工关卡按标准版执行：长文 Gate 1/2/3，卡片文章 Gate A/B；只认上一阶段成果出现后、用户当次明确点名下一步的确认，不承认概括式跨阶段授权。减少预览与交付不等于减少确认。
- 不将源文关于微信账号 API 权限、积分收费、平台条款或特定客户端机理的历史判断写成当前确定事实。需要回答这些问题时重新核验。
- 不复用固定去水印坐标；图像生成和编辑服从当前工具规则。
- 课程个案与半虚构叙事不得宣称为用户真实经历；来源声明不是事实校验的替代。

此文件用于追溯迁移选择，执行流程以 SKILL.md 及其专题参考文件为准。

## 2026-09-21 HTML 规则同步

核对 WorkBuddy 实际缓存与 `_专家/wechat-article-studio.zip` 的主文件、`04-html.md`、`05-publish-kit.md`、`08-selfcheck.md`，四份文件 SHA256 一致。把新增的 HTML 生成规则同步至 Codex `references/publishing.md`：块内裸文本与内联元素不混排、精简无意义 section 嵌套、不设置 `font-family`、相邻同背景段共用容器，以及官方检测器补充验证。旧“给 b 补字号”修法不再采用；本地 `wx_html_fix.py` 仅作启发式筛查，官方检测也不覆盖文档中的全部要求。

官方检测的本地封装 `工具脚本/wechat_official_verify.py` 在缓存缺失时会自动联网获取仓库、安装 npm 和浏览器依赖；Codex 版执行前须检查并按当前权限取得批准，不能把 WorkBuddy 的自动安装步骤当作默认授权。此次也同步较早遗漏的转发文案落位：新篇写入逐篇 `01_标题作者摘要.txt` 第 7 项，不再新建系列级 `04_转发文案.md`；既有文件不追溯改动。

用户进一步确认：今后**每篇新生成的公众号正文 HTML** 都做一次官方结构检测。Codex 版扩展为新生成／点名返工单篇交付前逐篇检测、修改后复检、系列正式交付前汇总检测；旧稿不自动追溯。Windows 运行设置 `PYTHONUTF8=1`，报告须同时显示零违规、零执行异常，不能仅凭脚本退出码判断通过；Chromium 检测不冒充 Android／iOS 微信真机预览。

## 2026-09-22 官方检测工具更新与本机验证

WorkBuddy 生效缓存与最新 `_专家/wechat-article-studio.zip` 的主文件及 `04-html.md`、`05-publish-kit.md`、`08-selfcheck.md`、`10-ops.md` SHA256 一致；项目 Codex 派生版的 `publishing.md` 已纳入探针、`dedupe` 和检测器未覆盖的 7 类规范，本轮把它同步到安装版，并补上只读／写回边界。

本机试跑发现共享脚本 `工具脚本/wechat_official_verify.py` 新版遗漏 `report()`，致浏览器检测后抛 `NameError`；已恢复报告函数，并阻止 `dedupe` 在可见文本不一致时写回。设置 `PYTHONUTF8=1` 后，`--setup` 探针通过；《手机方案》第 8 篇检测为违规 0、执行异常 0，`--dedupe --dry-run` 为 `nestNodes 0→0`、可见文本一致，正文试跑前后 SHA256 未变。实际写回模式未试跑，不能把 dry-run 结果视为写回验证。

## 两版同步规则（2026-09-10 用户确立）

WorkBuddy 专家版（`_专家/wechat-article-studio.zip` / `agents/wechat-article-studio.md`）是**标准版**；本 Codex 版是**派生版**。改动标准版时按以下规则同步，避免两版越走越远：

**必须同步（内容标准，与平台无关）** —— 改标准版时**同一轮内**同步到本版对应 references：

| 内容标准 | 本版落地位置 |
| --- | --- |
| 叙事真实性三分法与人物连续性 | `references/quality.md` §一 |
| 五层完整性、30% 降幅复核线、篇幅区间 | `references/quality.md` §七 |
| 文章类型分轨、叙事文替代验收标准 | `references/quality.md` §七、`references/editorial.md` |
| 去模板化、结构轮换、并列项核心动作、小标题与旁观视角 | `references/quality.md` §二、`references/editorial.md` |
| 标题三类轮换、备选标题须有据 | `references/quality.md` §三、`references/editorial.md` |
| 事实核验分级、适用与风险边界 | `references/quality.md` §四 |
| 系列规模与跨系列处理 | `references/editorial.md` |
| 发布包件数与卫生、微信正文规范、封面比例与安全区 | `references/publishing.md` |
| 巡检分类、清理安全流程 | `references/maintenance.md` |
| 工具脚本的参数与用途 | `references/publishing.md` |
| 后台派生卡片文章的定义、Gate、规格与数据边界 | `references/card-article.md`、`references/quality.md`、`references/publishing.md` |

**不同步（平台适配层）** —— 两版本就该不同，不互相抄：

- `present_files`、专家注册命令、CodeBuddy 专用元数据（displayName / profession / maxTurns）；
- WorkBuddy 私有 Python 解释器绝对路径（本版按当前工作区运行时定位）；
- 生图积分提示、绑死某一平台的固定裁切坐标与去水印命令（本版服从当前图像工具规则）；
- `agents/openai.yaml` 等 Codex 格式文件。

**冲突时**：以标准版为准，并在本文件记录差异原因（例如本版曾把发布包写成四件套、把水印写成"不自动去除"，均已按标准版修正）。

## 2026-09-14 内容标准同步

已同步 WorkBuddy“公众号学习工坊”首次反哺确认后的内容规则：文章类型分轨、叙事文三项替代验收、并列分论点核心动作检查、进程式／场景锚定式小标题、旁观者开头、具体事项罗列、承认不确定与“他人提问—自己回答”收尾，以及三类正文禁例。Codex 版只迁移平台无关的编辑标准，不复制 WorkBuddy 私有运行路径和注册流程；HTML 仍以 `section` 流式规范为准。

同日，WorkBuddy 又清理了主文件、README、规划、写作和发布细则中残留的 6 处旧 `table` 正向表述。Codex 版此前已统一采用 `section`，本次复核未改变正文排版规则；新增“架构级规则变更后跨文件扫描”的维护要求。现存 `table` 字样只允许用于禁用说明、历史迁移记录或 `table转section` 工具名。

## 2026-09-15 卡片文章与数据口径同步

同步 WorkBuddy 新增的“卡片文章（贴图）”形态、Gate A/B、逐篇随做迁移、唯一命名、纯文本描述、卡图逐张改编标注、数字回溯和分载体复盘。为避免三种“卡片”互相污染，Codex 版在说明中统一称为“正文内干货卡”与“后台派生卡片文章”；后者是同一长文的另一传播载体，不是第二篇文章、封面 A/B 或独立内容产线。磁盘目录仍保留 `卡片发布包/`，保证 WorkBuddy 现有工具兼容。

没有照搬 WorkBuddy 私有解释器、生图积分、固定去水印方法及尚待后台确认的平台判断。尺寸、字段、推荐与通知等易变口径在执行前以当前后台和官方说明复核；项目实测与编辑建议须显式分级。

## 2026-09-16 卡片文章双向同步

将《儿童情绪管理》《孩子摆烂怎么办》《孩子受欢迎能力培养》的实际制作反馈反哺 WorkBuddy 标准版：中间卡按“1个核心判断＋2—4个支撑块”组织，正文占可用区约45%—65%；本家庭教育项目默认无人物、弱时间线，封面／收尾用静物，中间卡用纯色或轻渐变；交付前按“最密卡原尺寸→逐篇预览→全系列合并预览”检查。

同时把 WorkBuddy 已验证的内容结构选卡型、特殊字符字形反向测试、高亮块按实际文字墨迹测量、几何问题先实测再调参等平台无关规则迁入 Codex 派生版。两边仍各自保留平台专用工具、路径、积分与运行方式，不做机械复制。
