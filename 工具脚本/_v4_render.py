# -*- coding: utf-8 -*-
"""v4 单条文案渲染器：把 DATA（创作内容）渲染成标准 6 节 MD。

数据模块提供 ITEMS = [ {...}, ... ]，每条字段：
  seq, dir, title(书名号短题), work(工作名/无书名号), src(素材来源句),
  span(时长抬头行), form(形态), point(一个点), danger(危险点抬头,可空),
  spoken(list[str]：口播行；'##LABEL' 形式表示结构标记独占一行),
  hooks(list[str] 钩子,通常1), ems(list[(整句,标色词)] 强调句),
  card(金句大字卡 (卡面, 挂句)) 或 None,
  colors(list[str] 全片标色词), cover(str 封面大字),
  short_titles(list[str]), desc(str 视频描述),
  top(置顶评论 整段字符串), tags(list[str]),
  moments(list[str] 朋友圈3段),
  pos(系列方案:发布序句), carry(承接方式句), openline, closeline,
  neighbors(list[(相邻,分工)]), coveracc(覆盖对账:4行tuple表),
  batch(连拍批次句), seg_note(分段素材说明:list[(文件,说明,时长)]),
"""
import importlib.util, io, os, sys, pathlib

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:/个人资料/家庭教育"
BASE = os.path.join(ROOT, "公众号", "手机方案", "视频号文案")


def spoken_block(lines):
    out = []
    for ln in lines:
        out.append(ln)
        out.append("")
    return "\n".join(out).rstrip()


def render(it):
    L = []
    L.append(f"# 视频号文案 · {it['seq']}《{it['work']}》")
    L.append("")
    L.append(f"> 系列《孩子与手机》· **发布序 {it['posnum']}/33** · 素材来源：**{it['src']}**")
    L.append(f"> **{it['span']}｜ 形态：{it['form']} ｜ 一个点：{it['point']}**")
    if it.get("danger"):
        L.append(f"> ⚠️ **危险点**：{it['danger']}")
    L.append("")
    L.append("---")
    L.append("")
    # 一、口播
    L.append("## 一、口播文案")
    L.append("")
    L.append(spoken_block(it["spoken"]))
    L.append("")
    L.append("---")
    L.append("")
    # 二、提词器（占位，gen_prompter 填）
    L.append("## 二、提词器文案")
    L.append("")
    L.append("（待 gen_prompter.py 生成）")
    L.append("")
    L.append("---")
    L.append("")
    # 三、上屏
    L.append("## 三、上屏方案")
    L.append("")
    L.append("- **版本**：金句")
    L.append("- **字幕位置**：画面下方（默认）")
    L.append("")
    L.append("### 开头钩子（前 3 秒大字，静音也看得见）")
    L.append("")
    for h in it["hooks"]:
        L.append(f"- 「{h}」停约 2.5 秒")
    L.append("")
    L.append("### 强调句")
    L.append("")
    for i, e in enumerate(it["ems"], 1):
        # em 可为 (上屏短句, 标色词, 挂句口播整行) 或 (整句, 标色词)
        if len(e) == 3:
            face, w, anchor = e
            L.append(f"{i}. 「{face}」 → “{w}”标暖色加粗")
            L.append(f"   - 挂在这句：「{anchor}」")
        else:
            sent, w = e
            L.append(f"{i}. 「{sent}」 → “{w}”标暖色加粗")
    L.append("")
    if it.get("card"):
        face, anchor = it["card"]
        L.append("### 金句大字卡（居中）")
        L.append("")
        L.append(f"1. 「{face}」 → 标暖橙；**停约 3.5 秒**")
        L.append(f"   - 挂在这句：「{anchor}」")
        L.append("")
    L.append("### 全片标色")
    L.append("")
    L.append("- " + "、".join(f'"{c}"' for c in it["colors"]) + " → 暖色加粗")
    L.append("")
    L.append("### 封面")
    L.append("")
    L.append(f"- 大字：**{it['cover']}**")
    L.append("")
    L.append("### 录制提示（念这几句就够）")
    L.append("")
    L.append(f"- 本条是**金句版**：只有「三、上屏方案 → 强调句」里那 **{len(it['ems'])} 句**"
             + (" ＋ 金句大字卡那 **1 句**" if it.get("card") else "")
             + "上字幕。录制时大致念到就行，别整句换成别的意思——锚点靠这几句定位。")
    L.append(f"- 必须念到的是：**那 {len(it['ems'])} 句强调句"
             + (" ＋ 金句卡挂句" if it.get("card") else "")
             + " ＋结尾安全提示**；**开头钩子那句不用念**（它是静音时看的字）。")
    L.append("")
    L.append("---")
    L.append("")
    # 四、合成
    L.append("## 四、视频合成方案")
    L.append("")
    L.append("> 用技能 **`ffmpeg-vertical-video-pipeline`** 合成，**不用剪映**。通用步骤见技能文档，这里只写本条特有的。")
    L.append("")
    nseg = len(it["seg_note"])
    L.append(f"**1. 素材（本条 {nseg} 段）**")
    L.append("")
    L.append("```")
    d = it["dir"]
    for i, (fn, desc, sec) in enumerate(it["seg_note"], 1):
        L.append(f"{d}/_素材/{i:02d}.mp4   {desc}    ≈{sec} 秒")
    L.append("```")
    L.append("")
    L.append("⚠️ **分段以「二、提词器文案」里的 `——第 N 段拍——` 为准，两处必须一致。**")
    L.append("")
    L.append("**2. 一条命令**（`--out` 指向 `_成品/`）")
    L.append("")
    L.append("```")
    L.append(r"cd C:\Users\ZhuanZ\.workbuddy\skills\ffmpeg-vertical-video-pipeline")
    L.append(r"python scripts/video_make.py ^")
    L.append(rf'  --md "D:\个人资料\家庭教育\公众号\手机方案\视频号文案\{d}\视频号文案_{it["seq"]}_{it["fileslug"]}.md" ^')
    L.append(rf'  --videos-dir "D:\个人资料\家庭教育\公众号\手机方案\视频号文案\{d}\_素材" ^')
    L.append(rf'  --out "D:\个人资料\家庭教育\公众号\手机方案\视频号文案\{d}\_成品\成片_{it["seq"]}.mp4" ^')
    L.append(r"  --set bitrate=10M --set zoom=0 --set preset=veryfast --set crf=21 ^")
    L.append(r"  --set visual.denoise=关闭 --set visual.xfade=0.5 --set visual.trim_tail=0.3 ^")
    L.append(r"  --set audio.preset=轻 --set audio.loudnorm.I=-14")
    L.append("```")
    L.append("")
    L.append("- ⛔ 码率用 `--set bitrate=10M`，**不要用** `--bitrate 10M`（后者静默失效）。")
    L.append("- ⛔ Python 要用带 faster-whisper 的那个绝对路径，否则**第 3 步 ASR 才报 ModuleNotFoundError**。")
    L.append("- 💡 先加 `--dump-params` 看一眼解析出的字幕／卡片对不对，再真跑。")
    L.append("")
    L.append("**3. 本条要特别交代的**")
    L.append("")
    for x in it["synth_notes"]:
        L.append(f"- {x}")
    L.append("- **BGM：本条不垫**（系列固定：全系列无 BGM）——⛔ **整节不写 `### 背景音乐`，不写＝没有**。")
    L.append("")
    L.append("---")
    L.append("")
    # 五、发布
    L.append("## 五、发布方案")
    L.append("")
    L.append("**短标题（≤16 字）**")
    L.append("")
    for i, st in enumerate(it["short_titles"], 1):
        L.append(f"{i}. **{st}**")
    L.append("")
    L.append("**视频描述（≤100 字）**")
    L.append("")
    L.append(f"> {it['desc']}")
    L.append("")
    L.append("**评论区置顶（发布后必发一条）**")
    L.append("")
    for row in it["top"].split("\n"):
        L.append(f"> {row}")
    L.append(f"**封面大字**：{it['cover']}")
    L.append(f"**话题标签**：" + " ".join(f"`{t}`" for t in it["tags"]))
    L.append("")
    L.append("**⭐ 朋友圈转发文案（一屏内、首行独立成立）**")
    L.append("")
    for row in it["moments"]:
        if row == "":
            L.append(">")
        else:
            L.append(f"> {row}")
    L.append("")
    L.append("- ⚠️ 与公众号侧同口径：**不复述视频描述**、**无广告腔**、**不索取互动**。")
    L.append("")
    L.append("---")
    L.append("")
    # 六、系列方案
    L.append("## 六、系列方案")
    L.append("")
    L.append("### 位置与衔接")
    L.append("")
    L.append(f"- **发布序**：**{it['posnum']}/33**（{it['pos']}）。")
    L.append(f"- **承接方式**：{it['carry']}")
    L.append("- **开场（已写进口播最前）**：")
    L.append(f"  > {it['openline']}")
    L.append("- **收尾（已写进口播最后）**：")
    L.append(f"  > {it['closeline']}")
    L.append("- ⛔ **判据不变**：把开场那句和收尾那句都删掉，本条**依然完整**。")
    L.append("")
    L.append("### 与相邻条的分工")
    L.append("")
    L.append("| 相邻 | 分工 |")
    L.append("|---|---|")
    for nb, dv in it["neighbors"]:
        L.append(f"| **{nb}** | {dv} |")
    L.append("")
    L.append("### 覆盖对账（本条 ∈ 系列）")
    L.append("")
    L.append("| | 内容 |")
    L.append("|---|---|")
    for k, v in it["coveracc"]:
        L.append(f"| **{k}** | {v} |")
    L.append("")
    L.append("### 通用拍摄规范")
    L.append("")
    L.append(f"- ⭐ **一次连拍 3~5 条**（同机位／光线／坐姿）——本条属**{it['batch']}**；⚠️ 相邻批之间**换一件衣服**。")
    L.append("- 分段拍、说错整段重录、头尾留白、不动机位、脸朝着光、构图留头顶——**见系列级文件，本条不重复**。")
    L.append("")
    return "\n".join(L)


def main():
    argv = sys.argv[1:]
    out_root = BASE
    if "--out-root" in argv:
        i = argv.index("--out-root")
        out_root = argv[i + 1]
        del argv[i:i + 2]
    data_path = argv[0]
    spec = importlib.util.spec_from_file_location("v4data", data_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    only = set(argv[1:])
    for it in mod.ITEMS:
        if only and it["seq"] not in only:
            continue
        d = os.path.join(out_root, it["dir"])
        os.makedirs(d, exist_ok=True)
        for sub in ("_素材", "_成品", "_过程文件"):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        p = os.path.join(d, f"视频号文案_{it['seq']}_{it['fileslug']}.md")
        pathlib.Path(p).write_text(render(it), encoding="utf-8")
        print("[write]", p)


if __name__ == "__main__":
    main()
