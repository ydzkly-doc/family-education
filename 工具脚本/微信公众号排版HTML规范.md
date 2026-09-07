# 微信公众号排版 HTML 规范（微信粘贴不塌版）

> ## ⚠️ 2026-09-05 重大修订：布局改用 `<section>` 流式，禁用 `<table>` 布局
> **实测血案**：旧"全 table 骨架"在**微信安卓 X5 内核**上会把 `<table>` 宽度固化，窄屏（360–410px）整列右裁——右侧文字/卡片被屏幕切掉、显示不全；iOS WebKit 会二次缩放所以正常。表现为"安卓左右显示不全、苹果正常"。
> **新标准**：正文布局一律 `<section style="box-sizing:border-box;width:100%;…">` 流式嵌套（卡片用 background/padding/border-radius/border-left），**禁止 `<table>/<tr>/<td>` 布局、禁止容器级固定宽 `width/max-width:≥200px`、禁止 `align="center"` 居中嵌套**；多列网格改纵向堆叠满宽 section。
> **转换工具**：旧 table 稿一键转 section：`python 工具脚本/table转section_微信正文流式重构.py <正文.html…>`（table/tr/td/div→section、剥固定宽与 data-*、竖条小标题转 border-left、多列网格转堆叠）。
> **预览重建**：`python 工具脚本/重建全部正文预览.py`。
> 以下"三类必排问题（A/C/B）"对 section 版依然适用（data-id、div、颜色挂容器），继续遵守；但"二、结构铁律"里的 table 骨架描述已被本节取代。
> 2026-09-05 已对 8 系列 71 篇正式正文全部转为 section 流式并校验合格（0 table/0 div/0 固定宽/0 data-id/section·p 配平），备份在 `_backup_table改section_20260905/`（孩子不上学系列源自 `_backup_微信规范化批量_20260904/`）。

---

> 适用：家庭教育工作空间全部公众号系列正文 HTML。成稿/交付前必须用配套脚本一键自检通过。
> 配套脚本：`工具脚本/微信HTML规范校验修复_wx_html_fix.py`
> 实证：青春期30讲、孩子不上学、非暴力沟通、爱的五种语言第1篇均已公众号实测验证。

## 一、三类必排问题（决策树，按 A→C→B 处理）

| 类型 | 特征 | 微信里表现 | 修法 |
|---|---|---|---|
| **A · data-id 残留** | grep `data-page-node-id`/`data-*` > 0（秀米/外部编辑器往返注入，连 body/head/meta 都有） | 微信把带 data-* 的节点当"外部组件"，**整段重置/剥样式**，头部白字整块消失 | 删全部 `data-page-node-id` 及 `data-*` 属性 |
| **C · div 骨架 + br 拆行** | `<div>` 多、`<p>` 少/为 0；白字标题 `<div/ p style="color:#fff">…<br>…` | div 的 color 微信继承最不稳；标题里 `<br>` 打断第二行白色继承 | ①`<div>/<h1-4>`→`<p>`；②白字标题的 `<br>` 拆成多个独立居中 `<p>`（一行一个） |
| **B · 颜色挂 td/section** | `<td/section/th style="…color:…">` 且内部是裸文字 | 微信对 td/section 的 color 向下继承不稳定，文字丢色 | color 下沉到包住文字的 `<p>/<span>/<b>/<strong>` 自身；td 只留背景/内边距/宽度 |

一篇可同时含多类，**顺序固定 A → C → B**（先剥 data-id，再 div/h 转 p、白字拆 br，最后颜色下沉）。脚本幂等，可重复跑。

## 二、结构铁律

- 骨架：外层满宽 `<table width="100%" style="background:页面底色">` → `<tr><td align="center" style="padding:24px 12px;">` → 内层 **680px 主表**（`max-width:680px;width:100%;border-collapse:collapse`，table 加 `role="presentation"`、`cellpadding=0 cellspacing=0 border=0`）。
- 主表显式 `text-align:left;`，防止外层居中继承给正文。
- **正文段落/小标题一律左对齐**；只有顶部标题块、金句块、陪伴卡、诗句、卡片标题在**该块自身 style** 写 `text-align:center;`。

## 三、标签白名单 / 黑名单

- **允许**：`table / tr / td / p / span / b / strong / br`。
- **禁止**：`<img>`（外链位图）、`class=`、`<style>` 块、`<div>`、`<ul>/<ol>/<li>`、`<h1>~<h4>`、任何 `data-*` 属性。
- 列表用 `<br>` + `·`/`①②③` 或 table 单元格实现。**全篇不使用 `<div>`**（任何位置都不写 div，文字一律 p/span/b/strong）。

## 四、颜色铁律（最关键）

- **文字颜色永远写在包住文字的 `<p>/<span>/<b>/<strong>` 的内联 style 上**。
- `<td>` 只承担 `background / padding / width / border / border-radius`，**不写 color**。
- 装饰竖条/空 td：只放 `background`+`width`、无文字、不写 color。
- **白字大标题**：一行一个独立 `<p>`，p 自身带 `color:#ffffff;text-align:center;display:block;`，**绝不在白字标题里用 `<br>` 拆多行**。
- 一个标签只能有一个 `style="…"`（禁止重复 style 属性，浏览器只认第一个）。
- 已自带 color 的强调标签（`<b>/<strong>`）内部文字，不要再用外层色 span 覆盖（否则金句强调色被正文色盖回）。

## 五、标准信息流（自上而下）

标题色块（坐标小字 + 主标题 + 「第X篇·共N篇|主题」）→ 开场叙事 → 台词卡（暖色）→ 竖条小标题×N → 正文段 → 方法/对照/流程 table 卡 → 「我后来试的几件小事」卡 → 金句居中块 → 预告/陪伴卡（灰底、无点赞转发指令）→ 来源声明（米白 `#faf9f6`+灰字、左对齐）。

## 六、一键自检 / 修复

```bash
# 体检（不改文件）：列出 A/B/C 及违禁标签、配平问题
python 工具脚本/微信HTML规范校验修复_wx_html_fix.py --check <文件.html...>

# 修复（幂等）：按 A→C→B 自动规范化
python 工具脚本/微信HTML规范校验修复_wx_html_fix.py <文件.html...>
```

合格输出 `✅ 文件名 (修复前: ...)`；不合格输出 `❌` 并列出修前/修后残留。
**交付标准：所有正文 `合格 N/N`，且 data-* = 0、td/section/th 带 color = 0、白字块 br = 0、无 div/h1-4/ul/img/class/style块、table/tr/td/p/span/b 标签配平。**

> 预览合并页（`<系列名>_全部正文预览_N篇.html`）仅本地校对、不发布，其导航外壳可用 class/div，不计入上述禁令。
