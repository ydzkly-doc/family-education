# memory 体积自动巡检（SessionStart Hook）

> 目的：防止 `MEMORY.md` 再次膨胀到超限、被**静默截断**导致记忆残缺。
> 建成：2026-09-14（起因：工作区 MEMORY.md 曾达 7776 字符 / 限额 3000，长期被截断而无人察觉）

---

## 一、为什么用 Hook 而不是定时任务

| 机制 | 触发时机 | 缺点 |
|---|---|---|
| **SessionStart Hook（本方案）** | **每次开新会话自动跑** | 依赖 WorkBuddy 桌面端在运行 |
| Automation 定时任务 | 按时间（如每周一 9:30） | **电脑关机/休眠就错过**，且检查时机与"记忆被读"的时刻无关 |

**关键理由**：memory 截断问题**恰恰发生在会话启动时**（记忆在这一刻被注入）。
定时任务可能在关机时错过，而 SessionStart 是**事件驱动**——只要用 WorkBuddy 就必然触发，且触发点与问题发生点完全重合。

---

## 二、装了什么

**① 脚本**：`工具脚本/memory体积巡检_check_memory.py`
| 模式 | 用途 |
|---|---|
| 无参 | 人类可读报告（手动巡检） |
| `--hook` | SessionStart 用；**仅在需行动时输出**，正常时完全静默 |
| `--json` | 脚本化调用 |

检查三件事：
- 工作区 `MEMORY.md` ≤ **3000** 字符
- 用户级 `~/.workbuddy/MEMORY.md` ≤ **4000** 字符
- memory 日志是否有超 **30 天**未归档的

**② Hook 配置**：`~/.workbuddy/settings.json` 的 `hooks.SessionStart`
```json
"hooks": {
  "SessionStart": [
    { "matcher": "startup",
      "hooks": [{ "type": "command",
        "command": "\"<python路径>\" \"D:/个人资料/家庭教育/工具脚本/memory体积巡检_check_memory.py\" --hook",
        "timeout": 20 }] }
  ]
}
```

---

## 三、日常表现

- **一切正常** → **完全静默**，不打扰你（这是设计：正常时不留痕迹）。
- **发现超限** → 在会话开头注入一条提醒，例如：
  > `[memory 体积巡检] ⚠️ 工作区 MEMORY.md 已达 3449 字符，超过注入限额 3000（超 449）——当前会话注入会被静默截断，记忆不完整。请先精简：细则移交专家包 SOP，只留项目约定与红线。`

---

## 四、验证它是否生效

**方法 1（最直接）**：开一个**新会话**。若当前 memory 正常，应**看不到任何提示**——这本身就是"已生效且一切正常"的表现。

**方法 2（主动触发报警）**：
```bash
# 临时把 MEMORY.md 撑大
python -c "p=r'D:\个人资料\家庭教育\.workbuddy\memory\MEMORY.md';open(p,'a',encoding='utf-8').write('字'*500)"
# → 开新会话，应看到 ⚠️ 提醒
# 验证完记得还原（从 _备份/ 取）
```

**方法 3（不依赖会话）**：直接手动跑
```bash
python 工具脚本/memory体积巡检_check_memory.py
```

---

## 五、如何关闭

编辑 `~/.workbuddy/settings.json`，删掉整个 `"hooks"` 字段即可。
改前版本备份在 `_备份/settings.json.bak_20260914_改前`。

> ⚠️ **注意**：Hook 改动**不会热加载**——WorkBuddy 在启动时抓取配置快照，
> 且需在 `/hooks` 面板确认后才生效。**改完请重启 WorkBuddy**。

---

## 六、维护备注

- 若脚本路径或 python 路径变化，需同步改 `settings.json` 里的 command。
- 脚本**只读**：不修改、不删除任何文件，只输出提醒。
- **退出码恒为 0**：SessionStart hook 的非零退出码会被当作执行失败，故改用 stdout 传递提醒。
