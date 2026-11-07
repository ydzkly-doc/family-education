# -*- coding: utf-8 -*-
"""
video_script_lift_check.py  —— 口播「读懂重讲 / 不许截取」检测

用途：检查视频号口播的【叙述句】是不是把公众号原文截下来换词。
判据：口播每一行去掉引号台词后，若与对应原文出现【连续 N 个汉字重合】，即判截取。
合法豁免（SOP 3.4）：
  ① 「」『』内的照念台词、孩子引语；
  ② 全片通用的高频短语（阈值内不算）；
  ③ 行内【】拍摄提示。

用法：
  python video_script_lift_check.py <口播.md>            # 单条
  python video_script_lift_check.py <目录>               # 目录下所有 .md
退出码：发现违规返回 1（供 check 钩子/脚本调用）。
"""
import sys, os, re, glob, argparse


def _force_utf8_streams():
    """Windows 控制台默认 GBK（cp936）时，打印 ⚠️/❌/✅ 会抛 UnicodeEncodeError。
    统一把 stdout/stderr 切到 UTF-8，并对无法编码的字符降级替换，保证不崩。
    （Python 3.7+ 的 TextIOWrapper.reconfigure；管道/重定向同样适用）"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


THRESH = 8          # 连续重合汉字数阈值（>= 判截取；6~7字多为口语自然撞车）
CJK = re.compile(r"[\u4e00-\u9fff]+")

# 全系列通用、不具“原文指纹”的短语：固定金句、方法术语、并列短词。
# 命中这些不算“截取原文叙述”——它们要么是观众要照抄的口诀，要么本就只能这么说。
COMMON = [
    # —— 全系列固定金句/口诀（方法标签，观众照抄）——
    "考成什么样家都在", "先接情绪再谈事", "只说事不翻旧账",
    "当教练不当裁判", "人和事分开", "放礼花",
    "坏消息进得了家门", "坏消息能进家门",
    # —— 学校/家庭通用名词与并列短词 ——
    "第一次月考", "高一", "高中生", "亲子", "家庭教育",
    "怪老师怪同学", "老师当面批评", "睡觉吃饭",
    "情绪低落", "心理老师",
]


def cjk_only(s):
    return "".join(CJK.findall(s))


def load_source_text(md_path, md_text):
    """根据 md 头部“第N篇”定位公众号正文 html，提取纯汉字序列。

    兼容两种历史写法：
      · 旧：`素材来源：**公众号第8篇…`
      · 现行：`素材来源：**第8篇《…》`
    `素材来源：**编辑原创**`（开头条等不指向单篇的）返回 (None, None)。
    """
    m = re.search(r"素材来源：\*\*(?:公众号)?第(\d+)篇", md_text)
    if not m:
        return None, None, None
    n = int(m.group(1))
    # 从 视频号文案/0X_xxx/ 向上两级到系列根，再找 公众号文章/发布包_第N篇_*/长图文发布包/正文_*.html
    series_root = os.path.abspath(os.path.join(os.path.dirname(md_path), "..", ".."))
    pat = os.path.join(series_root, "公众号文章", "发布包_第%d篇_*" % n,
                       "长图文发布包", "正文_*.html")
    hits = glob.glob(pat)
    if not hits:
        return n, None, None
    html = open(hits[0], encoding="utf-8").read()
    html = re.sub(r"</p>", "\n", html)
    txt = re.sub(r"<[^>]+>", "", html)
    return n, cjk_only(txt), split_clauses(txt)


def strip_quotes(line):
    """删除引号内照念台词与拍摄提示，返回待检测的叙述文本。"""
    line = re.sub(r"【[^】]*】", "", line)
    line = re.sub(r"「[^」]*」", "", line)
    line = re.sub(r"『[^』]*』", "", line)
    line = re.sub(r'"[^"]*"', "", line)
    return line


def explained_by_common(seg):
    """该重合片段是否本质上由白名单短语造成（假阳性）。
    满足任一即豁免：
      ① seg 去掉白名单词后残长 < THRESH；
      ② seg 是某个 >= THRESH 白名单词的子串（如金句被截掉首尾）；
      ③ 某个白名单词是 seg 的子串，且 seg 仅比它多出 < THRESH 字。"""
    residual = seg
    for w in sorted(COMMON, key=len, reverse=True):
        residual = residual.replace(w, "")
    if len(residual) < THRESH:
        return True
    for w in COMMON:
        if len(w) >= THRESH:
            if seg in w or w in seg:
                if abs(len(seg) - len(w)) < THRESH:
                    return True
    return False


def longest_common_run(clause, src_clauses):
    """在【单个源分句】内找最长连续重合片段（汉字），已剔除白名单假阳性。

    ⚠️ 为什么必须「分句对分句」（2026-11-06 修）：
      早期把整行与整篇都剥成纯汉字串再比，标点一剥就跨句粘连——
      实测「手机放回固定位置，站起来接水、洗漱、收书包，」被拼成
      「手机放回固定位置站起来接水洗漱」15 字，误报为截取。
      「连续重合」按定义不可能跨标点，所以两侧都按分句比对。
    """
    L = len(clause)
    for size in range(L, THRESH - 1, -1):
        for i in range(0, L - size + 1):
            seg = clause[i:i + size]
            if explained_by_common(seg):
                continue
            for sc in src_clauses:
                if seg in sc:
                    return seg
    return ""


def split_clauses(text):
    """把文本切成「分句」级的纯汉字串：标点、数字、拉丁字母都是边界。
    CJK.findall 天然按非汉字断开，正好就是分句边界。"""
    return CJK.findall(text)


def parse_koubo(md_text):
    """取“## 一、口播文案”到下一个 --- / ## 之间的行。"""
    m = re.search(r"##\s*一、口播文案\s*(.*?)(?:\n---|\n##\s)", md_text, re.S)
    if not m:
        return []
    lines = []
    for raw in m.group(1).splitlines():
        s = raw.strip()
        if not s:
            continue
        lines.append(s)
    return lines


def list_lift_fails(md_path):
    """供 video_script_check 调用：返回该文件叙述句截取违规的描述列表（静默）。"""
    out = []
    md_text = open(md_path, encoding="utf-8").read()
    n, _src, src_clauses = load_source_text(md_path, md_text)
    if src_clauses is None:
        return out          # 定位不到原文时不阻塞主校验
    for idx, line in enumerate(parse_koubo(md_text), 1):
        if "lift:ignore" in line:
            continue
        for clause in split_clauses(strip_quotes(line)):
            if len(clause) < THRESH:
                continue
            hit = longest_common_run(clause, src_clauses)
            if hit:
                out.append("[防截取] 第%d行连续重合%d字：%s" % (idx, len(hit), hit))
                break
    return out


def check_file(md_path):
    md_text = open(md_path, encoding="utf-8").read()
    n, _src, src_clauses = load_source_text(md_path, md_text)
    print("=== %s ===" % os.path.basename(md_path))
    if src_clauses is None:
        if n is None:
            if "编辑原创" in md_text:
                print("  · 编辑原创条（不指向单篇原文），跳过截取检测。")
            else:
                print("  ⚠️ 未找到「素材来源：…第N篇」，跳过。")
        else:
            print("  ⚠️ 定位不到第%d篇正文 html，跳过。" % n)
        return 0
    bad = 0
    for idx, line in enumerate(parse_koubo(md_text), 1):
        if "lift:ignore" in line:
            continue
        for clause in split_clauses(strip_quotes(line)):
            if len(clause) < THRESH:
                continue
            hit = longest_common_run(clause, src_clauses)
            if hit:
                bad += 1
                print("  ❌ 第%2d 行 连续重合 %d 字：%s" % (idx, len(hit), hit))
                print("       原行：%s" % line)
                break
    if bad == 0:
        print("  ✅ 叙述句无 >=%d 字截取重合（台词/引语已豁免）。" % THRESH)
    else:
        print("  合计 %d 处疑似截取 → 按“读懂重讲”重落字。" % bad)
    return bad


def main():
    global THRESH
    _force_utf8_streams()
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--thresh", type=int, default=THRESH)
    args = ap.parse_args()
    THRESH = args.thresh

    target = args.target
    if os.path.isdir(target):
        mds = sorted(glob.glob(os.path.join(target, "**", "视频号文案_*.md"), recursive=True))
    else:
        mds = [target]
    total_bad = 0
    for f in mds:
        total_bad += check_file(f)
    print("\n%s：%d 个文件，%d 处疑似截取。" %
          ("不通过" if total_bad else "通过", len(mds), total_bad))
    sys.exit(1 if total_bad else 0)


if __name__ == "__main__":
    main()
