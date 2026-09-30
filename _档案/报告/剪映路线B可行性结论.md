# 剪映「路线B（写文件生成工程）」可行性结论

> 调查日期：2026-09-24
> 环境：剪映专业版 **11.5.0.14471**（`D:\Program Files\JianyingPro`，另有 11.3.0.14362 并存）
> 草稿目录：`D:\Program Files\JianyingPro Drafts`（配在 `User Data\Config\globalSetting` 的 `currentCustomDraftPath`）

---

## 一句话结论

**❌ 在剪映 11.5 上不可行。剪映强制要求 `draft_content.json` 为密文，写入明文会被静默拒绝。**
**且加密不是可配置项，没有开关可以关掉。**

（"路线B" = 绕过界面、直接用脚本写出剪映工程文件来生成视频；"路线A" = 模拟鼠标键盘操作界面）

---

## 二、关键事实（实测）

### 1. 剪映 11.5 加密了草稿核心文件

| 文件 | 状态 |
|---|---|
| `draft_content.json` | **密文**（100% 可打印字符、base64 特征、非 JSON） |
| `draft_meta_info.json` | **密文** |
| `Timelines/<UUID>/draft_content.json` | **密文**（与顶层同源） |
| `template-2.tmp` | **密文**（1136 B，与 draft_content.json 同大小） |
| ⭐ `Timelines/<UUID>/template.tmp` | **明文完整结构**（3959 B） |
| `timeline_layout.json` / `key_value.json` / `draft_settings` / `draft_agency_config.json` | 明文 |

- 加密**只针对** `draft_content.json` 与 `draft_meta_info.json` 这两个核心文件。
- 密文体积远小于明文（1136 B vs 3959 B）→ 推测为 **加密 + 压缩**，回推明文不可行。

### 2. 明文不生效的对照实验（决定性）

| 草稿 | 与源草稿的唯一差别 | 结果 |
|---|---|---|
| `路线B_对照_纯复制` | 无（全部字节原样，含密文） | ✅ **正常打开** |
| `路线B_验证_明文` | **仅** `draft_content.json` 换为明文（9:16 画布） | ❌ **点击无反应，打不开** |

两个副本的 UUID、`draft_meta_info.json`、目录引用**全部保持原样**，唯一变量是文件格式。
→ **结论确定：剪映 11.5 拒绝明文 `draft_content.json`。**

### 3. 剪映其实"读到"了明文，只是弃用

- `.backup/` 下出现 **9 个** `2026…_7527cb9e….load.bak`：`7527cb9e` 正是写入明文文件的 **md5 前缀**，4002 B 正是该文件大小，内容**逐字就是写入的明文** → 它反复加载了明文
- `User Data\Log\draft_acion_watch.json` 记录该草稿 `"type":"copy_draft_external"`、`"suc":true`、`"errno":0` → 登记成功
- 剪映按写入的**新 UUID** 建出了 `.backup/<新UUID>/` → 说明 `project.json` / `timeline_layout.json` 都被正确读取
- ⛔ 但剪映**从未回写/加密** `draft_content.json` → 说明它从未成功保存，即"拿到了但解码失败弃用"

### 4. 加密不可配置

扫描 196 个文本配置文件（`User Data\Config` 等）中 `encrypt / cipher / aes / decrypt` 等关键词：
**仅匹配到几个自身就被 AES 加密的无关配置文件，未发现任何可关闭的加密开关。**

---

## 三、已获取的可复用资产

### 剪映 11.5 草稿结构（明文 schema）

样本：`_资产/剪映11.5草稿结构样本.json`（提取自 `Timelines/<UUID>/template.tmp`）

顶层 36 个字段，结构与经典 `draft_content.json` **完全一致**：

```
canvas_config  画布（width/height/ratio）
config         导出/识别等开关（含 subtitle_recognition_id、lyrics_*）
materials      55 个子键（videos / audios / texts / effects / stickers / canvases …）
tracks         轨道数组（本样本为空）
keyframes      8 个子键（videos / audios / texts / effects / filters …）
duration / fps / id / name / create_time / draft_type …
```

### 草稿内部 UUID 引用关系（写生成器必备）

- `Timelines/project.json`：`id`(project) / `main_timeline_id` / `timelines[].id`
- `timeline_layout.json`：`activeTimeline` / `dockItems[].timelineIds[]`
- **时间线 UUID 同时就是 `Timelines/<UUID>/` 目录名** → 改 UUID 必须**三处同步**
- `.backup/timeline_backup_manifest.json` 也以 UUID 为键
- 取 UUID 的方法：读 `timeline_layout.json` 的 `activeTimeline`

### 其他环境事实

- **剪映自带 ffmpeg**：`D:\Program Files\JianyingPro\11.5.0.14471\ffmpeg.exe`（v21.7）
  - ⚠️ **阉割版**：只有硬件编码器（`h264_amf/mf/nvenc/qsv`，**无 libx264**）
  - ⚠️ **无 `subtitles` / `ass` / `drawtext` 滤镜** → **不能烧字幕、不能画文字**
  - ✅ 有 `concat`、`silencedetect`、`loudnorm`、`mp4` muxer
- **剪映草稿列表的显示名取自文件夹名**（不是密文 meta 里的名字）→ 命名可控
- 剪映的 `.alog` 日志是**二进制/加密**的，`strings` 提取 **0 命中**，排查时别浪费时间

---

## 四、结论与后续可选方向

**路线B 在 11.5 上封死。** 后续可考虑：

| 方向 | 说明 | 评价 |
|---|---|---|
| **完整版 ffmpeg 全自动合成** | 装带 `libx264 + libass` 的 ffmpeg，用 ASS 字幕实现"关键指标暖色"等要求，程序化完成拼接/剪停顿/字幕/金句卡/封面/1080×1920 | 推荐；**唯一缺口是语音识别（ASR）拿字幕时间码** |
| **混合：剪映只做字幕识别** | 用剪映「智能字幕」导出 SRT（每篇手工一次，约 1 分钟），其余全部程序化 | 务实；剪映的 ASR 是其最有价值且免费的能力 |
| **降级剪映至 ≤5.9** | 旧版未加密，理论上路线B 可用 | 不推荐：需下载旧版、功能少、可能强制升级、可能破坏现有环境 |
| **路线A：GUI 自动化操作** | 已验证「视觉 + 坐标 + 注入」闭环可用 | 慢、脆、需授权抢焦点，对批量生产价值低 |

### 复活条件

若**未来剪映版本取消加密**（或用户换用未加密版本），路线B 即刻复活。
用 `工具脚本/jianying_draft_inspect.py <草稿名>` 可随时复查 `draft_content.json` 是明文还是密文。

---

## 五、相关脚本（`工具脚本/`）

| 脚本 | 用途 |
|---|---|
| `jianying_draft_inspect.py` | **检查草稿是否加密 / 结构如何**（可传参，用于复查路线B 复活条件） |
| `jianying_gui_probe.py` | 进程 + 窗口 + UIA 控件树 + 截图（`--shot`） |
| `jianying_zorder_probe.py` | z 序 / 遮挡判定 / 光标注入（**点击前安全检查**） |
| `jianying_capture_keytest.py` | `PrintWindow` 抓窗口内容（抗遮挡）+ 键盘注入验证 |

> 注：`test.mp4`（`测试/`）经抽帧证实为**紫薯烹饪教程**，与同目录的《别再说装病》口播文案**不配套**，仅作占位素材。
