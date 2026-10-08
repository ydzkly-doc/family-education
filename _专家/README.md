# `_专家/` —— 专家包的**仓库快照**（供版本管理 / 换电脑恢复）

> ⚠️ **这里的文件是副本，不是源。** 不要直接改 `plugins/` 里的文件——
> 改了会在下次同步时**被覆盖**。要改就改本机真相源，再跑同步脚本。

---

## 目录里有什么

```
_专家/
  plugins/<包名>/        # 4 个专家包的「完整解压快照」——⭐ 这一份进 git
  还原到本机.py           # 换电脑：把快照写回本机 marketplace / cache
  README.md              # 本文件
  *.zip / *.bak          # 本地构建产物与旧备份（⛔ 不进 git，仅留本机）
```

| 专家包 | 真相源（本机） |
|---|---|
| `wechat-article-studio` | `cache/my-experts/wechat-article-studio/<版本>/` |
| `video-script-studio` | `cache/my-experts/video-script-studio/<版本>/` |
| `wechat-learning-studio` | `cache/my-experts/wechat-learning-studio/<版本>/` |
| `family-education-learning-planner` | `marketplaces/.../plugins/family-education-learning-planner/`（**从未进 cache**） |

---

## 为什么用「解压快照」而不是 zip

- 解压快照能**逐文件 diff / review**——谁改了哪个 SOP、哪句台词，版本历史里看得清；
- zip 只能整体替换，历史看不出改了什么，还原还得先解压；
- zip 仍会在本机生成（构建产物），但**不再进 git**（见 `.gitignore` 的 `_专家/*.zip`）。

---

## 日常：改完专家后怎么同步（仓库根目录）

```bash
PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
"$PY" 工具脚本/expert_pack_sync.py            # 源 → marketplace → plugins快照 → zip → 逐文件比对
"$PY" 工具脚本/expert_pack_sync.py --check    # 只比对不写入（提交前预检）
```

看到 **PASS** 后，提交快照：

```bash
git add _专家/plugins
git commit -m "专家同步：<改了什么>"
git push
```

- 只刷新仓库快照、不碰 marketplace/zip：`--snapshot-only`
- 不重打包 zip：`--no-zip`
- ⚠️ 专家包**不热加载**，改完**下个会话**才生效。

---

## ⭐ 换新电脑：怎么恢复

1. 装好 WorkBuddy，`git clone` 本仓库；
2. 先预检（只看会改什么）：

```bash
"$PY" _专家/还原到本机.py --check
```

3. 确认无误后执行：

```bash
"$PY" _专家/还原到本机.py
```

它会把 `plugins/<包>/` 写回本机：
- `marketplaces/my-experts/plugins/<包>/`
- `cache/my-experts/<包>/<版本>/`（版本号取自 `plugin.json`，可用 `--version` 覆盖）

4. **重启 WorkBuddy**，4 个专家即出现。

> `family-education-learning-planner` 只写 marketplace（它从不进 cache）。
> 还原是**整体覆盖**：目标里未提交的本地改动会被覆盖，所以先跑 `--check`。

---

## 三条纪律

1. ⛔ **只改真相源，不改 `plugins/` 快照**；改完跑 `expert_pack_sync.py`。
2. ⭐ **提交前先同步**——否则仓库里是旧版，换电脑拿到的也是旧版。
3. **同步/还原脚本都入库**，换电脑后流程不变（路径用 `~`，无需手改）。

---

## 与 `_技能/` 的区别

| | 专家包 | 技能 |
|---|---|---|
| 入库形式 | 解压快照 `_专家/plugins/<包>/` | 明文快照 `_技能/<技能名>/` |
| 同步命令 | `工具脚本/expert_pack_sync.py` | `工具脚本/skills_sync.py` |
| 换电脑 | `_专家/还原到本机.py` | `skills_sync.py --src <新源目录>` |
