# `_技能/` —— 用户级技能的**仓库快照**（供版本管理）

> ⚠️ **这里的文件是副本，不是源。**
> **不要直接改这里**——改了会在下次同步时**被覆盖**。

---

## 为什么要这个目录

技能的**源**在用户级目录：

```
C:/Users/ZhuanZ/.workbuddy/skills/<技能名>/
```

它**不在本仓库里**，所以技能的任何改动：**进不了 git、没法 diff、换机器就丢**。

→ 本仓库保留一份**明文快照**，跟着项目一起提交、一起 push。

---

## 当前快照

| 技能 | 文件数 | 说明 |
|---|---|---|
| `ffmpeg-vertical-video-pipeline` | 13 | 口播短视频自动合成管道（`scripts/` ＋ `SKILL.md` ＋ `reference/`） |
| `family-education-learning-coach` | 13 | 家庭教育两年学习系统教练（`SKILL.md` ＋ `references/` ＋ `assets/templates/`）。状态目录固定在 `家庭教育学习系统/`。⭐ **同时镜像进专家包** `family-education-learning-planner/skills/` |

---

## ⭐ 第二类目标：专家包镜像（2026-09-29 立）

有些技能要被**打进专家包**（专家包要自包含，如 `family-education-learning-planner/skills/family-education-learning-coach/`）。
这类副本与 `_技能/` 快照一样，**由同一个脚本单向镜像**——所以磁盘上有多份，**真相源永远只有用户级那一份**。

镜像目标写在 `工具脚本/skills_sync.py` 的 `MIRROR_TARGETS`。新增带技能的专家包时加一行即可：

```python
MIRROR_TARGETS = {
    "family-education-learning-coach": [
        # ① 建包/注册/重新打包 zip 用的那棵
        "…/marketplaces/my-experts/plugins/<包名>/skills",
        # ② 应用装载后运行的那棵（要等专家被装载过才出现，不存在则跳过）
        "…/cache/my-experts/<包名>/<版本>/skills",
    ],
}
```

⚠️ **两条注意**：
1. ⛔ **不要直接改专家包里的技能副本**——下次同步会被覆盖。改源，再跑脚本。
2. **目标父目录不存在时会跳过**（不凭空创建 `cache/` 结构），等应用装载过该专家后自动开始镜像。

只同步快照、跳过专家包镜像：加 `--local-only`。

---

## ⭐ 同步动作（改完技能后照这个做）

### 一条命令（仓库根目录下）

```bash
python 工具脚本/skills_sync.py
```

它会：① 对比源与快照 → ② 列出「新增／修改／删除」→ ③ 复制过去，并删掉源里已经没有的文件。

### 提交前先预检（只看差异、不写）

```bash
python 工具脚本/skills_sync.py --check
```

- **退出码 0** = 已一致；**非 0** = 快照落后，需要先同步
- 想保留目标里多出来的文件（不删）：加 `--no-delete`

### 然后照常提交推送

```bash
python git_sync.py -m "技能同步：<改了什么>"
```

### 换机器时

技能源路径会变 → 用 `--src` 指过去：

```bash
python 工具脚本/skills_sync.py --src "D:/某处/.workbuddy/skills"
```

---

## 三条纪律

1. ⛔ **改技能请改「源」**（`~/.workbuddy/skills/<技能名>/`），**然后跑同步**；
   直接改 `_技能/` 里的文件，下次同步会被覆盖。
2. ⭐ **技能被升级后要记得同步**——否则仓库里是旧版，回溯时会误判
   （本目录是别人升级技能后最容易漏掉的一步）。
3. **同步脚本本身也入库**（`工具脚本/skills_sync.py`），换机器后流程不变。

---

## 与专家包的区别（两种产物，别混）

| | **专家包** | **技能** |
|---|---|---|
| 源 | `~/.workbuddy/plugins/cache/my-experts/`（不在仓库） | `~/.workbuddy/skills/`（不在仓库） |
| 入库形式 | **打包 zip** → `_专家/*.zip` | **明文快照** → `_技能/<名>/` |
| 同步方式 | 手工三步：改 cache → 同步 marketplace → 重打包 zip | **一条命令**：`工具脚本/skills_sync.py` |
| 为什么这样 | 专家包要**整包分发** | 技能**需要 diff**（脚本改动要看得出来） |

> 两者共同的坑：**源都在用户目录**，都靠"额外一步"才进仓库 —— 所以都容易漏。
> 专家包那边靠"每次改都重打包"的习惯；技能这边靠本目录的同步命令。
