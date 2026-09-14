from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACCOUNT = "归途有光·和孩子一起重启"
SERIES = "幸福的方法·一个爸爸的重启笔记"

META = {
    1: ("你只想要个成绩好的我", "孩子说“你只想要一个成绩好的我”，他真正问的是什么", "成绩之外，孩子还在确认自己的价值", "什么都给了孩子，为什么他还是觉得自己不被爱", "成绩掉下来以后，先别急着问他为什么不用功", "课程中的孩子在成绩下降后说：你只想要一个成绩好的我。真正刺痛他的，往往不只是一次批评，而是担心自己的价值只剩分数。先把成绩问题、情绪状态和亲子关系分开处理。", "王金海讲书《幸福的方法》课程案例；泰勒·本-沙哈尔《幸福的方法》。"),
    2: ("等孩子考上大学就好了", "“等孩子考上大学就好了”，这句话为什么总不兑现", "忙碌奔波型：目标负责指路，不负责替代生活", "目标一个个实现，我们为什么还是停不下来", "别把幸福永远安排在下一站", "从考高中、考大学到找到工作，“等……就好了”总把幸福推到下一站。《幸福的方法》的忙碌奔波型提醒我们：目标负责指路，不该吞掉过程。给家庭同时安排未来任务和当下补给。", "王金海讲书《幸福的方法》；泰勒·本-沙哈尔《幸福的方法》中的幸福类型框架。"),
    3: ("打游戏专注写作业喊累", "孩子打游戏能专注，写作业就喊累：先别急着说他懒", "从“懒”退一步，检查目标、反馈与难度", "同一个孩子，为什么在游戏和作业前像两个人", "把游戏的反馈机制借一点给学习，不等于纵容游戏", "孩子打游戏投入、写作业却拖延，不足以证明他故意偷懒。游戏常提供清楚目标、及时反馈和匹配难度，学习却可能目标模糊或难度失衡。先诊断卡点，再把任务改成够得着的小关。", "王金海讲书《幸福的方法》；心流条件参考相关综述与元分析（Fong等，2015）。"),
    4: ("又要优秀又要快乐", "又想孩子优秀，又想他快乐，真的只能二选一吗", "感悟幸福型：同时照顾当下体验与未来收益", "“快乐”和“有前途”并不是必然冲突", "MPS三问：从意义、快乐与优势里试出方向", "《幸福的方法》的四种人生模型提醒我们：只苦现在或只顾眼前，都不是唯一选项。用意义、快乐和优势三组问题帮助孩子探索方向，而不是替他选定职业；再一起做一个可复盘的小实验。", "泰勒·本-沙哈尔《幸福的方法》中的四种人生模型与MPS过程；王金海讲书《幸福的方法》。"),
    5: ("你脸上有没有光", "想让孩子幸福，父母先别把自己活成一张疲惫的脸", "父母先照顾自己的状态，孩子才看得到另一种生活", "孩子听见的不只是道理，还有家里的情绪天气", "父母不必表演快乐，但要学会处理自己的压力", "父母讲再多积极道理，孩子每天感受到的仍是家里的情绪天气。课程案例里，母亲焦虑、父母互相指责，孩子只想关门。父母先照顾压力、修复伴侣协作，再把具体感谢说出来。", "王金海讲书《幸福的方法》课程案例；Diener与Seligman（2002）Very Happy People。"),
    6: ("幸福是练出来的", "幸福不是等来的：一份不靠打卡的7天家庭练习", "把幸福从口号变成低压力、可复盘的日常动作", "别再逼自己积极，这7天只练习看见和调整", "把幸福落到日常：记录、简化、连接和恢复", "幸福练习不等于强迫积极，也不是七天改变家庭。用一周做低压力实验：记录快乐与意义、写下三件好事、简化一项负担、安排一次连接，并在最后只保留真正有用的一个动作。", "王金海讲书《幸福的方法》；泰勒·本-沙哈尔《幸福的方法》；Seligman等（2005）Positive Psychology Progress。"),
}


def e(text):
    return escape(text, quote=False)


def render_line(line):
    parts = line.split("|")
    kind, value = parts[0], parts[1]
    if kind == "P":
        return f'<section style="box-sizing:border-box;width:100%;padding:5px 24px 1px"><p style="font-size:16px;line-height:1.9;margin:0 0 12px;color:#3a332b;text-align:left">{e(value)}</p></section>'
    if kind == "H":
        return f'<section style="box-sizing:border-box;width:100%;padding:18px 24px 7px"><p style="font-size:19px;line-height:1.55;margin:0;font-weight:bold;color:#8d642f;text-align:left">{e(value)}</p></section>'
    if kind == "Q":
        return f'<section style="box-sizing:border-box;width:100%;padding:13px 24px"><section style="box-sizing:border-box;width:100%;padding:20px 18px;background:#f5ede0;border-left:4px solid #c99a5b"><p style="font-size:17px;line-height:1.85;margin:0;font-weight:bold;color:#8d642f;text-align:center">{e(value)}</p></section></section>'
    if kind == "N":
        return f'<section style="box-sizing:border-box;width:100%;padding:20px 24px 9px"><section style="box-sizing:border-box;width:100%;padding:14px 16px;background:#fff6e9;border:1px solid #ead5b4"><p style="font-size:13px;line-height:1.8;margin:0;color:#795a34;text-align:left">{e(value)}</p></section></section>'
    if kind == "C":
        items = "".join(f'<p style="font-size:15px;line-height:1.85;margin:0 0 9px;color:#4e453b;text-align:left">{e(item)}</p>' for item in parts[2:])
        return f'<section style="box-sizing:border-box;width:100%;padding:8px 24px"><section style="box-sizing:border-box;width:100%;padding:18px 18px 10px;background:#fbf6ee;border:1px solid #e7d8bf;border-radius:8px"><p style="font-size:16px;line-height:1.65;margin:0 0 10px;font-weight:bold;color:#8d642f;text-align:left">{e(value)}</p>{items}</section></section>'
    raise ValueError(f"unknown block: {kind}")


def article_html(number, meta, lines):
    slug, title, theme, _, _, _, sources = meta
    body = "\n".join(render_line(line) for line in lines if line.strip())
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title></head>
<body style="margin:0;padding:0;background:#f7f4ef">
<section style="box-sizing:border-box;width:100%;padding:20px 12px;background:#f7f4ef"><section style="box-sizing:border-box;width:100%;background:#fffdf9;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
<section style="box-sizing:border-box;width:100%;padding:30px 24px 26px;background:#a47a3a;text-align:center">
<p style="font-size:13px;line-height:1.6;letter-spacing:2px;margin:0 0 12px;color:#f0e0c6;text-align:center">幸福的方法 · 一个爸爸的重启笔记</p>
<p style="font-size:24px;line-height:1.5;margin:0 0 12px;font-weight:bold;color:#ffffff;text-align:center">{e(title)}</p>
<p style="font-size:13px;line-height:1.7;margin:0;color:#ecd9b8;text-align:center">第 {number} 篇 · 共 6 篇｜{e(theme)}</p></section>
{body}
<section style="box-sizing:border-box;width:100%;padding:22px 24px 28px"><section style="box-sizing:border-box;width:100%;padding:16px;background:#f2eee8;border-top:1px solid #ded4c7">
<p style="font-size:13px;line-height:1.8;margin:0 0 6px;color:#6d645b;text-align:left">本文为课程与读书资料整理，不是对个体的诊断或治疗建议。</p>
<p style="font-size:13px;line-height:1.8;margin:0;color:#6d645b;text-align:left">本文参考：{e(sources)}课程与书籍内容版权归原作者及相关权利方所有。</p>
</section></section></section></section></body></html>'''


def fields_text(number, meta):
    slug, title, _, alt1, alt2, digest, sources = meta
    return f'''【状态】
现行标准升级版；沿用原封面，未重新生成封面图。

【标题】
{title}

【作者／署名】
{ACCOUNT}

【正文叙事者】
一个也在重启的爸爸（学习与整理视角；课程案例和改编场景不冒充亲历）

【摘要】
{digest}

【备选标题】
1. {alt1}
2. {alt2}

【来源】
{sources}

【原文链接】
留空

【合集】
{SERIES}（共6篇）

【正文文件】
正文_第{number}篇_{slug}.html

【封面文件】
封面_第{number}篇_{slug}.jpg
'''


def main():
    source_dir = ROOT / "_过程文件" / "升级正文块"
    for number, meta in META.items():
        slug = meta[0]
        lines = (source_dir / f"{number:02d}.txt").read_text(encoding="utf-8").splitlines()
        package = ROOT / f"发布包_第{number}篇_{slug}"
        (package / f"正文_第{number}篇_{slug}.html").write_text(article_html(number, meta, lines), encoding="utf-8")
        (package / "01_标题作者摘要.txt").write_text(fields_text(number, meta), encoding="utf-8")
        print(package)


if __name__ == "__main__":
    main()
