# -*- coding: utf-8 -*-
"""生成《你就是孩子最好的玩具》读书笔记系列 第3-7篇 发布包正文 HTML。
统一骨架：外层页底表 -> 680主表(text-align:left) -> 标题色块 -> 内容(全 table 卡片 + p 段落)。
所有视觉元素 table 化；正文 p 段左对齐；金句/标题/陪伴卡块内显式居中。
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# 色板（赤陶棕暖色系）
C_PAGE = "#f5f3ef"      # 页面底
C_CARD = "#fdfaf5"      # 主表底/暖白
C_MAIN = "#b06a48"      # 主色
C_MAIN_D = "#93553a"    # 深赤陶（小标题/金句字）
C_MAIN_D2 = "#8a4f33"   # 更深（卡片标题）
C_TXT = "#3a322c"       # 正文
C_TXT2 = "#5a4636"      # 卡内正文
C_LIGHT = "#faf3ec"     # 浅底块
C_BORDER = "#ecd9c6"    # 浅边框
C_LIGHT2 = "#f0e2d4"    # 几件小事底
C_AMBER_BG = "#fef6ec"  # 台词卡底
C_AMBER_BAR = "#d9963f" # 台词卡竖条
C_AMBER_T = "#b4730f"   # 台词卡标题字
C_AMBER_TX = "#8a5a2e"  # 台词卡正文字
C_GREY_BG = "#f4f6f5"   # 陪伴卡底
C_GREY_T = "#5f6a62"
C_GREY_TX = "#6b7268"
C_DECL_BG = "#faf9f6"   # 来源声明底
C_DECL_T = "#9a9890"
C_TITLE_SUB = "#f3e2d4" # 标题色块小字
C_TITLE_SUB2 = "#ecd3c0"

def p(text, size=16, color=C_TXT, mb=12, align="left", bold=False, lh=1.9, center=False):
    a = "text-align:center;display:block;" if center else f"text-align:{align};"
    fw = "font-weight:bold;" if bold else ""
    return f'<p style="margin:0 0 {mb}px;font-size:{size}px;line-height:{lh};color:{color};{fw}{a}">{text}</p>'

def title_block(title_lines, coord):
    lis = "\n".join(
        f'<p style="margin:0 0 {6 if i<len(title_lines)-1 else 16}px;color:#ffffff;font-size:25px;font-weight:bold;line-height:1.5;text-align:center;display:block;">{t}</p>'
        for i, t in enumerate(title_lines))
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_MAIN};">
<tr>
<td style="padding:30px 28px 26px;">
<p style="margin:0 0 10px;color:{C_TITLE_SUB};font-size:13px;letter-spacing:2px;text-align:center;display:block;">归途有光 · 和孩子一起重启</p>
{lis}
<p style="margin:0;color:{C_TITLE_SUB2};font-size:13px;text-align:center;display:block;">{coord}</p>
</td>
</tr>
</table>'''

def book_intro(kind, body_html):
    """kind: 'first' 用大块；这里系列首篇已用，其余用承接式。body_html 为内部内容。"""
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_LIGHT};border:1px solid {C_BORDER};">
<tr>
<td style="padding:18px 20px;">
{body_html}
</td>
</tr>
</table>'''

def sub_head(text):
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;margin:6px 0 12px;">
<tr>
<td style="padding:0;">
<table width="100%" style="width:100%;border-collapse:collapse;">
<tr>
<td style="width:6px;background:{C_MAIN};padding:0;font-size:0;line-height:0;">&nbsp;</td>
<td style="padding:2px 0 2px 12px;">
<p style="margin:0;font-size:18px;font-weight:bold;color:{C_MAIN_D};line-height:1.5;text-align:left;">{text}</p>
</td>
</tr>
</table>
</td>
</tr>
</table>'''

def quote_card(title, text):
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_AMBER_BG};border-left:4px solid {C_AMBER_BAR};margin:6px 0 14px;">
<tr>
<td style="padding:16px 20px;">
<p style="margin:0 0 6px;font-size:14px;color:{C_AMBER_T};font-weight:bold;text-align:left;">{title}</p>
<p style="margin:0;font-size:16px;line-height:1.9;color:{C_AMBER_TX};text-align:left;">{text}</p>
</td>
</tr>
</table>'''

def things_card(items_html):
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_LIGHT2};margin:8px 0 16px;">
<tr>
<td style="padding:18px 20px;">
<p style="margin:0 0 12px;font-size:16px;font-weight:bold;color:{C_MAIN_D2};text-align:center;display:block;">我后来试着做的几件小事</p>
{items_html}
</td>
</tr>
</table>'''

def thing(text, last=False):
    mb = 0 if last else 10
    return f'<p style="margin:0 0 {mb}px;font-size:15px;line-height:1.9;color:{C_TXT2};text-align:left;">{text}</p>'

def golden(lines):
    inner = "\n".join(
        f'<p style="margin:0 {("0 4px" if i<len(lines)-1 else "0")};font-size:19px;font-weight:bold;line-height:1.8;color:{C_MAIN_D};text-align:center;display:block;">{t}</p>'
        for i, t in enumerate(lines))
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_LIGHT};margin:8px 0 16px;">
<tr>
<td style="padding:24px 28px;">
{inner}
</td>
</tr>
</table>'''

def companion(lines):
    inner = "\n".join(
        f'<p style="margin:0 {("0 6px" if i<len(lines)-1 else "0")};font-size:14px;line-height:1.9;color:{C_GREY_TX};text-align:center;display:block;">{t}</p>'
        for i, t in enumerate(lines))
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_GREY_BG};margin:10px 0 16px;">
<tr>
<td style="padding:20px 22px;">
<p style="margin:0 0 8px;font-size:15px;font-weight:bold;color:{C_GREY_T};text-align:center;display:block;">归途有光 · 和孩子一起重启</p>
{inner}
</td>
</tr>
</table>'''

def declare_text(note):
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_DECL_BG};margin:10px 0 0;">
<tr>
<td style="padding:16px 20px;">
<p style="margin:0;font-size:13px;line-height:1.8;color:{C_DECL_T};text-align:left;">来源声明：本文为读书笔记与学习心得，整理自扶鹰教育 · 王金海讲书对《你就是孩子最好的玩具》（[美]金伯莉·布雷恩 著）的讲解，核心观点版权归原作者及出版方所有，非原文摘录，仅用于知识普及与学习交流。{note}</p>
</td>
</tr>
</table>'''

def page(title, coord, body, decl_note):
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;">
<table width="100%" style="background:{C_PAGE};border-collapse:collapse;margin:0;padding:0;">
<tr>
<td align="center" style="padding:24px 12px;">

<table width="680" style="width:680px;max-width:100%;border-collapse:collapse;background:{C_CARD};text-align:left;">
<tr>
<td style="padding:0;">

{title_block(None, coord) if False else ""}
<!--TITLE-->

<table width="100%" style="width:100%;border-collapse:collapse;background:{C_CARD};">
<tr>
<td style="padding:26px 26px 8px;">

{body}

{declare_text(decl_note)}

</td>
</tr>
</table>

</td>
</tr>
</table>

</td>
</tr>
</table>
</body>
</html>'''

def compare_table(title, left_head, right_head, rows, left_head_bg=C_MAIN, right_head_bg="#6b8f6a"):
    """两列对照表。rows: [(left, right), ...]"""
    trs = [
        '<tr>'
        f'<td style="padding:8px 10px;background:{left_head_bg};font-weight:bold;border:1px solid {left_head_bg};text-align:left;"><span style="color:#ffffff;">{left_head}</span></td>'
        f'<td style="padding:8px 10px;background:{right_head_bg};font-weight:bold;border:1px solid {right_head_bg};text-align:left;"><span style="color:#ffffff;">{right_head}</span></td>'
        '</tr>'
    ]
    for i, (l, r) in enumerate(rows):
        bg = C_LIGHT if i % 2 == 0 else C_CARD
        trs.append(
            '<tr>'
            f'<td style="padding:8px 10px;border:1px solid {C_BORDER};background:{bg};text-align:left;"><span style="color:{C_TXT};">{l}</span></td>'
            f'<td style="padding:8px 10px;border:1px solid {C_BORDER};background:{bg};text-align:left;"><span style="color:{C_TXT};">{r}</span></td>'
            '</tr>')
    return (
        f'<table width="100%" style="width:100%;border-collapse:collapse;background:{C_LIGHT};border:1px solid {C_BORDER};margin:8px 0 16px;">'
        f'<tr><td style="padding:14px 16px 6px;">'
        f'<p style="margin:0 0 10px;font-size:15px;font-weight:bold;color:{C_MAIN_D};text-align:center;display:block;">{title}</p>'
        f'</td></tr>'
        f'<tr><td style="padding:0 16px 16px;">'
        '<table width="100%" style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.7;">'
        + "".join(trs) +
        '</table></td></tr></table>'
    )

def build(folder, fname, title, title_lines, coord, body, decl_note="文中“我家孩子”为帮助共情的同路人化叙事，非纪实。"):
    tb = title_block(title_lines, coord)
    html = page(title, coord, body, decl_note).replace("<!--TITLE-->", tb)
    d = os.path.join(BASE, folder)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, fname)
    open(path, "w", encoding="utf-8").write(html)
    print("written:", path)
    return path

# ============ 第 3 篇：否定感受 ============
def intro3():
    return book_intro("x",
        '<p style="margin:0 0 8px;font-size:16px;line-height:1.6;color:%s;font-weight:bold;text-align:center;display:block;">📖 读书笔记 ·《你就是孩子最好的玩具》第 3 篇</p>'
        '<p style="margin:0;font-size:14px;line-height:1.8;color:#8a5a3a;text-align:left;">前两篇说了控制和放任，这一篇聊一个更隐蔽、我们几乎天天在犯的误区——<b>否定孩子的感受</b>。金伯莉·布雷恩说，孩子愿不愿意跟你说话，往往就是被一句句“不疼别哭”慢慢关上的。</p>' % C_MAIN_D)

body3 = "\n".join([
    p("儿子小时候，有一次在小区门口摔了一跤，膝盖蹭破一大块皮，眼泪在眼眶里打转。我脱口而出：“哎呀没事没事，男孩子勇敢点，不疼，自己爬起来。”"),
    p("他爬是爬起来了，但那个把眼泪硬生生憋回去的表情，我到现在都记得。"),
    p("后来他长得比我高了，我才发现一件怪事：他在外面受了委屈、考试砸了、跟同学闹别扭，回到家一个字都不说。我问急了，他就一句“没事”。我那时候还怪他：“这孩子怎么什么都不跟家里讲？”"),
    p("读《你就是孩子最好的玩具》这一章，我心里咯噔一下——他不是天生不爱说，是我从小一句句教他“别说”的。"),
    intro3(),
    sub_head("“不疼，别哭”——我们以为在安慰，其实在否认"),
    p("书里举了几个我们熟得不能再熟的场景：孩子摔疼了哇哇哭，大人说“你都是小大人了，有什么好哭的”；刚吃完饭一小时孩子喊饿，我们说“怎么可能饿，你不是刚吃过”；孩子怕黑不敢一个人睡，我们笑他“胆子怎么这么小”。"),
    p("金伯莉提醒我们：这些话的共同点，是<b>急着让孩子接受我们认定的“事实”，而绕开了他真实的感受</b>。可感受这东西有个倔脾气——你不承认它，它不会消失，只会被压到心里去。"),
    p("孩子一次次收到的信号是：“我说疼，你说不疼；我说怕，你说别怕。那我说出来有什么用？反正你也不信。”久而久之，他就不再说了。等到青春期你盼着他跟你掏心窝子，那扇门早就从里面插上了。"),
    golden(["“摔得不疼”这句话，", "否定的不是那一跤，", "是孩子对你的信任。"]),
    sub_head("被否认的感受，会变成“情绪内耗”"),
    p("书里用了一个词，叫<b>情绪内耗</b>。当一个孩子反复被告知“你的感受不对、不重要”，他心里会慢慢长出一个声音：我的感觉是错的，我这个人也不那么重要。"),
    p("这种孩子表面上很乖、不闹，但心里没底、缺乏安全感。他不是没有情绪，是不敢有情绪；不是不难过，是觉得难过也没用。这比哭出来、闹出来，其实更让人担心。"),
    p("金伯莉说，真正的接纳是把孩子当成一个和我们平等的人——他的疼是真的，他的怕是真的，他的委屈也是真的。先接住这个“真”，后面的教育才有地方落脚。"),
    quote_card("💬 孩子哭了/说“我好烦/我好怕”时，我后来照着说",
        "“来，爸看看。是真的挺疼的对不对？想哭就哭一会儿，爸在这儿。”／“你现在心里特别烦，能跟我说说吗？说不出来也没关系，我陪着你。”——先承认感受，不急着讲道理、不急着让他“好起来”。"),
    sub_head("我后来试的几件小事，都笨，但有用"),
    things_card("".join([
        thing("<b>① 把“不疼/别怕/这有什么”从嘴边删掉。</b>换成“是挺疼的”“你现在很难过吧”。就这一个改动，孩子愣了好几次——他好像第一次发现，我是站在他这边的。"),
        thing("<b>② 蹲下来、或者坐下，跟他平视。</b>书里特别强调这一条：认真聆听时，身体要跟孩子视线齐平，眼睛看着他。居高临下说“我理解你”，和蹲下来看着他眼睛说，分量完全不一样。"),
        thing("<b>③ 他说“没事”时，不追问，只留门。</b>我会说一句“好，你不想说就先不说，什么时候想说爸都在”，然后真的走开、不盘问。奇怪的是，门留着，他反而过一会儿自己凑过来了。", last=True),
    ])),
    p("我慢慢懂了：孩子的情绪就像洪水，堵是堵不住的，越堵越凶；你能做的是给他一条能流走的河道。而这条河道，就是“我的感受有人接得住”。"),
    p("下一篇，聊一个我们最信、却可能伤孩子最深的办法——奖励。你可能也常说“考好了给你买……”，但书里那个“老人给踢球孩子发钱”的故事，让我后背发凉。"),
    companion(["那些年我叫他“别哭”的时刻，其实他最想要的，", "不过是有人蹲下来，说一句“我知道你疼”。", "愿我们都能成为那个，接得住孩子眼泪的人。"]),
])
build("发布包_第3篇_别哭关上心门", "正文_第3篇_别哭关上心门.html",
      "孩子哭时你说“不哭”，其实是在关上他的心门",
      ["孩子哭时你说“不哭”，", "其实是在关上他的心门"],
      "《你就是孩子最好的玩具》读书笔记 · 第 3 篇 · 共 7 篇｜接纳感受",
      body3)

# ============ 第 4 篇：外部奖励 德西效应 ============
body4 = "\n".join([
    p("我儿子上小学那会儿，我最得意的一套“育儿经”是这样的：考试进前十名，奖一双他想要的球鞋；乖乖把作业写完，奖励看半小时平板；好好吃完饭，能换一颗糖。"),
    p("说实话，特别管用。一说有奖，他动作快得像换了个人。我还暗自得意，觉得自己掌握了调教孩子的密码。"),
    p("直到他上了初中，有一次我又说“这次期末考好点，爸给你换台新电脑”，他头也没抬，回了我一句：“那我不考好，是不是就啥也没有？那我图啥。”"),
    p("我愣在原地。那一瞬间我说不清哪里不对，但隐约觉得，有个东西被我一点点喂没了。"),
    book_intro("x",
        '<p style="margin:0 0 8px;font-size:16px;line-height:1.6;color:%s;font-weight:bold;text-align:center;display:block;">📖 读书笔记 ·《你就是孩子最好的玩具》第 4 篇</p>'
        '<p style="margin:0;font-size:14px;line-height:1.8;color:#8a5a3a;text-align:left;">这一篇说第三个误区：<b>用外部奖励和物质刺激去“驱动”孩子</b>。金伯莉在书里明确批评了这种做法——它短期立竿见影，长期却在悄悄掏空孩子做事的内在动力。心理学上有个专门的名字，叫“德西效应”。</p>' % C_MAIN_D),
    sub_head("那个给踢球孩子“发工资”的老人"),
    p("书里讲了个故事，我看完后背发凉。一位老人喜欢安静，可每天放学后，总有一群孩子在他窗前的草坪上踢球、吵闹。老人没去赶他们，反而走出去，给每个孩子发了点钱，说：“我特别喜欢看你们在这儿踢球，你们来了我特别开心，这是谢礼。”孩子们高兴坏了。"),
    p("第二天孩子们又来了，老人给的钱少了一点。第三天更少。到第四天，老人摊摊手说：“我实在没钱给你们了。”第五天起，孩子们再也没来踢球——他们气鼓鼓地说：“没钱？那谁还白给你踢！”"),
    p("你看出来了吗？孩子们一开始踢球，是<b>因为喜欢、因为好玩</b>，这是内在动力。老人用钱，把“我喜欢踢”偷偷换成了“我为了钱踢”。等钱一撤，他们连原本的热爱也一起丢了。"),
    golden(["外在的那颗糖，", "会一点点换走、最后扑灭，", "孩子心里原本的那团火。"]),
    sub_head("我们家的“球鞋和平板”，干的是同一件事"),
    p("我对照自己，冷汗都下来了。“考好了奖球鞋”“写作业换平板”——我不就是那位老人吗？学习本来可以因为“弄懂了一道题的爽”“考好了的成就感”而有意思，可我一次又一次地在旁边递糖，告诉他：学习本身不划算，得靠外面的奖赏才值得做。"),
    p("书里讲，这就是<b>德西效应</b>：当一个人因为外部奖励才去做某件事，他内在的兴趣和动力反而会被削弱。奖励一停，行为就停。孩子没有学会“我为什么要学”，只学会了“我能换点什么”。"),
    p("金伯莉也没把话说绝——不是完全不能奖励。关键在于怎么奖：<b>越快兑现、越像交易的奖励越伤人；越慢、越聚焦于“努力过程”的肯定越养人。</b>"),
    quote_card("💬 把“交易式奖励”换成“看见努力”，我后来这样说",
        "不再说“考 100 分奖你 XX”，而是在他做完之后具体地描述：“我注意到你这道题卡了二十分钟都没放弃，最后自己做出来了，这股劲儿真厉害。”——夸的是他的努力、方法和坚持，不是分数，更不提前开价。"),
    sub_head("奖励的正确打开方式"),
    compare_table(
        "奖励孩子，错在哪、怎么改",
        "尽量少用", "可以多做",
        [
            ("事前开价：“考好奖你 XX”", "事后肯定努力本身"),
            ("只奖结果（分数、名次）", "奖过程（坚持、方法、进步）"),
            ("同一件事反复奖、立刻兑现", "延迟、偶尔、重精神肯定"),
        ],
        left_head_bg=C_MAIN, right_head_bg="#6b8f6a"),
    p("我后来还学书里的办法，把“奖励”从物质换成了陪他一起看见成长——比如用一张简单的自律表，记录他在“专注、坚持”这些能力上的小进步。奖的不再是东西，是“我又做到了一次”的那种感觉。"),
    things_card("".join([
        thing("<b>① 停掉事前“开价”。</b>不再说“你做到 X 我就给你买 Y”。这是最难忍的，头两周他动力明显掉了一点，但那是在等糖——熬过去，他自己的劲儿才回得来。"),
        thing("<b>② 夸具体，不夸笼统。</b>不说“你真棒”，改说“你今天主动把错题改完了，没让我催”。具体到行为，孩子才知道自己哪儿做对了。"),
        thing("<b>③ 帮他尝到“成就感”本身。</b>他做出一道难题、考完自我感觉不错时，我会停下来问一句：“靠自己搞定的感觉，怎么样？”让他记住那种内在的爽。", last=True),
    ])),
    p("教育的终点，不是养出一个“给够糖才肯走”的孩子，而是养出一个心里有火、自己愿意往前走的人。那颗糖，我决定慢慢从他手里拿走了。"),
    p("下一篇聊最后一个误区——惩罚。“考差了就别想去游乐园”为什么越罚越不服管？书里给了一个特别妙的替代办法：让“直接后果”说话。"),
    companion(["别让奖品替孩子走路。", "他心里那团“我想、我能、我做到了”的火，", "比任何一双球鞋都值钱。"]),
])
build("发布包_第4篇_奖励偷走内动力", "正文_第4篇_奖励偷走内动力.html",
      "奖励越多孩子越不想学？一颗糖偷走内动力",
      ["奖励越多，孩子越不想学？", "那颗糖，正偷走他心里的火"],
      "《你就是孩子最好的玩具》读书笔记 · 第 4 篇 · 共 7 篇｜奖励与内动力",
      body4)

# ============ 第 5 篇：消极惩罚 vs 直接后果 ============
body5 = "\n".join([
    p("上学期期末，我儿子考砸了。出成绩那天，我脑子一热，撂下一句狠话：“考成这样，周末说好的游乐园别去了，在家好好反省！”"),
    p("他当时没顶嘴，只是盯着我看了两秒，那眼神我现在都忘不了——不是愧疚，是一种“你不讲理”的不服气。然后他冷冷地说：“考砸跟游乐园有什么关系？你就是想罚我。”"),
    p("我被噎住了。是啊……考砸跟游乐园，到底有什么关系？我答不上来，但我嘴上不能输，还是硬着头皮把他押在了家里。那个周末谁都不好过，他没反省，我也没解气。"),
    book_intro("x",
        '<p style="margin:0 0 8px;font-size:16px;line-height:1.6;color:%s;font-weight:bold;text-align:center;display:block;">📖 读书笔记 ·《你就是孩子最好的玩具》第 5 篇</p>'
        '<p style="margin:0;font-size:14px;line-height:1.8;color:#8a5a3a;text-align:left;">四大误区的最后一个：<b>用“跟错事毫不相干的后果”来惩罚孩子</b>。金伯莉把它叫“消极后果”。她说，这么罚不仅没用，还会把孩子脑子里的因果逻辑搅乱，甚至教会他撒谎。替代办法，叫“直接后果”。</p>' % C_MAIN_D),
    sub_head("“考差了就取消游乐园”，错在哪儿"),
    p("书里点破：当惩罚和孩子做错的事之间<b>没有任何道理上的关联</b>时，孩子是理解不了的。“为什么我没考好，就不能去游乐园了？”这两件事在他心里根本连不上。他唯一能学到的是——大人力气大、说了算；以及，下次别被抓到。"),
    p("于是越罚越不服管，越罚越会藏。金伯莉说，很多孩子的撒谎、掩盖，就是从“害怕不相干的惩罚”里学来的：反正认了也没好果子，不如编个谎蒙混过去。"),
    p("我回想自己常干的事：犯错就没收手机、成绩不好就取消旅行、一不高兴就关他禁闭。手机、旅行、游乐园……跟他犯的错，八竿子打不着。我以为这叫“立规矩”，其实只是在发泄“我不高兴”。"),
    golden(["惩罚制造恐惧，教孩子怎么躲；", "后果长出责任，教孩子怎么扛。"]),
    sub_head("书里那个“到点就走”的家庭"),
    p("那正确的做法是什么？金伯莉给了个特别妙的概念，叫<b>直接后果</b>——让孩子承担的，是他的行为<b>自然长出来的结果</b>，而不是大人硬塞的惩罚。"),
    p("书里举了个例子：全家约好上午十一点出门吃饭，到点了孩子还在看电视，磨磨蹭蹭假装没听见，叫了几次都不动。这时候怎么办？不是吼、不是骂、也不是“下次不许看电视”。"),
    p("答案是——<b>十一点，你们到点就走（前提是孩子安全有保障）</b>。等他看完电视出来，已经十二点，家里人都吃完了。这时你温和地告诉他：“我们说好十一点出门的，你没准备好，那这顿你只能自己在家面对了。”"),
    p("饿一顿肚子，是“不守约”这件事自己带来的结果。这里头没有怒气、没有报复，孩子却清清楚楚地看到：哦，我的选择，会带来这样的后果。他服气，也才真正学会守约和负责。"),
    quote_card("💬 把“我要罚你”换成“这是你的选择带来的结果”",
        "“咱们说好十一点出门，你选择继续看电视，那我们就先走了。结果是你这顿得自己在家解决——这不是罚你，是没守约自然会发生的事。下次你想赶上，就提前准备好。”"),
    sub_head("直接后果 vs 消极惩罚，一眼分清"),
    compare_table(
        "直接后果 vs 消极惩罚",
        "消极惩罚（别用）", "直接后果（推荐）",
        [
            ("考差了 → 取消游乐园", "不起床迟到 → 自己面对迟到"),
            ("犯错了 → 没收手机", "乱扔玩具 → 玩具收走一周"),
            ("家长发泄怒气、强加的", "行为自然长出、事先说清的"),
        ],
        left_head_bg="#b06a48", right_head_bg="#6b8f6a"),
    p("当然有个底线：直接后果不能伤害孩子的安全和身心。把孩子一个人丢在危险的地方、用羞辱和断绝关系来要挟，那不是后果，那是伤害。我们要的是“安全范围内，让他体验选择的结果”。"),
    things_card("".join([
        thing("<b>① 立规矩时，先把“后果”一起说好。</b>不是等事发了再临时想招罚他，而是提前讲清：“咱们十点出门，到点没准备好，我们就先走。”孩子心里有数，后果才是他自己选的。"),
        thing("<b>② 后果要跟错事“连得上”。</b>忘带作业，自然结果是自己去跟老师解释，而不是罚他一个月不打球。连得上，他才长记性。"),
        thing("<b>③ 执行时不带怒气，语气温和而坚定。</b>发火就变味成惩罚了。我练的是心里默念：“我不是要赢他，是要让他看清因果。”", last=True),
    ])),
    p("后来再遇到类似的事，我试着不用“我要罚你”，而是平静地让结果发生。奇怪，他反而开始为自己的事上心了——因为那不再是“跟爸的对抗”，而是“他自己的人生”。"),
    p("到这里，四个误区都说完了。下一篇是这个系列最“能直接用”的一篇——金伯莉给出的情感引导五步法：孩子情绪上头的那一刻，我们到底该怎么说、怎么做。"),
    companion(["我们不必做不发脾气的完美父母，", "只需要在罚他之前先问一句：", "“这个后果，跟他做错的事，连得上吗？”"]),
])
build("发布包_第5篇_让后果说话", "正文_第5篇_让后果说话.html",
      "考差了就取消游乐园？孩子不服，是你罚错了",
      ["考差了就取消游乐园？", "孩子不服，是你罚错了"],
      "《你就是孩子最好的玩具》读书笔记 · 第 5 篇 · 共 7 篇｜惩罚与直接后果",
      body5)

# ============ 第 6 篇：情感引导五步法 ============
def step_table():
    rows = [
        ("① 提前告知", "出门前先讲清楚待会儿会发生什么、你希望他怎么做。进电影院前先说“里面人多，要保持安静”，出门讲一遍、进场前再确认一遍。", "播下种子，让孩子心中有数"),
        ("② 关注判断", "平时就观察他：什么情况下最容易烦躁、什么事会让他炸？了解他的脾气，才能在情绪起来之前有准备。", "读懂孩子，而不是只看行为"),
        ("③ 认真聆听", "蹲下来、和他视线齐平，眼睛看着他，先听后说，不打断、不急着下结论。他表达的过程，就是情绪宣泄的过程。", "先听后说，身体先蹲下来"),
        ("④ 体察理解", "他情绪上头时，先接住感受而不是讲道理。帮他把情绪说出来：“你现在是不是特别委屈？”情绪被准确命名，就会慢慢平复。", "命名情绪，先共情后讲理"),
        ("⑤ 引导解决", "永远从换位思考出发，让他在安全感里自己想办法；可以给有限的选择，而不是替他决定。情绪无错，行为有界。", "陪他解决，不替他解决"),
    ]
    tds = []
    for i,(name, desc, key) in enumerate(rows):
        bg = C_LIGHT if i%2==0 else C_CARD
        tds.append(
            '<tr>'
            f'<td style="padding:10px 10px;font-weight:bold;border:1px solid {C_BORDER};background:{bg};vertical-align:top;white-space:nowrap;"><span style="color:{C_MAIN_D};">{name}</span></td>'
            f'<td style="padding:10px 10px;border:1px solid {C_BORDER};background:{bg};vertical-align:top;"><span style="color:{C_TXT};">{desc}</span><br><span style="color:{C_AMBER_T};font-size:13px;">▸ {key}</span></td>'
            '</tr>')
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_LIGHT};border:1px solid {C_BORDER};margin:8px 0 16px;">
<tr><td style="padding:14px 16px 6px;">
<p style="margin:0 0 6px;font-size:15px;font-weight:bold;color:{C_MAIN_D};text-align:center;display:block;">情感引导五步法（建议收藏）</p>
</td></tr>
<tr><td style="padding:0 16px 16px;">
<table width="100%" style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.7;">
{''.join(tds)}
</table>
</td></tr>
</table>'''

body6 = "\n".join([
    p("前阵子一个晚上，我正在跟客户打一个很重要的电话，我儿子在客厅里戴着耳机打游戏，赢了，激动得大喊大叫，还绕着沙发跑。我当时火一下就上来了，捂住话筒冲他吼了一句：“吵什么吵！没看见我在打电话吗！”"),
    p("他像被按了暂停键，瞬间蔫了，老老实实坐回沙发，一声不吭。我转身继续对着电话，语气立刻又变得客气温柔。"),
    p("电话打完我回头看他，他抱着膝盖坐在角落，没看电视，也没玩游戏，就那么安静地坐着。我忽然有点心虚——我对一个素未谋面的客户那么耐心，对自己儿子却只有吼。"),
    book_intro("x",
        '<p style="margin:0 0 8px;font-size:16px;line-height:1.6;color:%s;font-weight:bold;text-align:center;display:block;">📖 读书笔记 ·《你就是孩子最好的玩具》第 6 篇</p>'
        '<p style="margin:0;font-size:14px;line-height:1.8;color:#8a5a3a;text-align:left;">前面把四个坑都讲完了，这一篇是这本书最值钱的部分——金伯莉给出的<b>情感引导五步法</b>。它不靠吼、不靠哄、不靠交易，而是教孩子认识情绪、说出情绪，再陪他一起解决问题。</p>' % C_MAIN_D),
    sub_head("吼完那一嗓子，孩子心里在想什么"),
    p("书里说，像我那样吼，看似立竿见影，孩子立刻安静了。可他心里其实装满了问号：为什么爸爸突然发火？为什么他对电话里的人那么温柔，对我那么凶？他是不是不爱我了？"),
    p("他安静下来，<b>不是因为知道自己错了，而是因为害怕失去爱</b>。所以下次他还会犯——他压根没明白“在别人打电话时吵闹”这件事本身有什么问题，他只记住了“爸发火很吓人”。"),
    p("那情感引导式的父母会怎么做？金伯莉给的示范是：先平复自己的情绪，然后蹲下来跟孩子说——"),
    quote_card("💬 书里的示范话术（孩子吵闹时）",
        "“爸爸知道你今天特别开心（先接住情绪）。不过爸爸现在正在打电话，你这样会吵到我们，而且你在屋里跑来跑去容易摔着，爸爸会担心（说清原因和担心）。你先自己安静玩一会儿玩具，等爸爸打完电话，就来陪你一起玩，好吗（给出选择和约定）？”"),
    p("你看，这一段话里没有训斥，却让孩子明白了三件事：我的开心被理解了、我为什么不该这样、接下来我可以怎么做。更重要的是，他不会怀疑爸爸不爱他。<b>只有在安全感里，孩子才学得会认识自己和别人的情绪。</b>"),
    sub_head("情感引导五步法"),
    p("金伯莉把这套方法拆成五个步骤。我把它整理成了下面这张表，建议你收藏——它几乎能应对孩子哭闹、发脾气、耍赖、胆小这些日常场景。"),
    step_table(),
    golden(["你可以生气，", "但不能打人；", "情绪没有对错，行为要有边界。"]),
    p("书里还特别叮嘱：五个步骤听着多，其实抓住三个核心就够用了——<b>提前告知、倾听理解、引导解决</b>。我自己的体会是，最关键也最难的，是第四步“先接住情绪”。我们太容易在孩子情绪刚冒头时就跳去讲道理、下判断，可一个正在气头上、哭得上气不接下气的孩子，是什么道理都听不进去的。"),
    p("先让他知道“我的感受被看见了”，情绪的洪水退下去，道理的种子才播得进去。"),
    things_card("".join([
        thing("<b>① 情绪上头时，先处理情绪，再处理事情。</b>把“你怎么又这样”咽回去，先说“我看到你现在很……”。这一步我练了很久，经常还是会破功，但破功了我会回去补一句“爸刚才急了”。"),
        thing("<b>② 给情绪“起名字”。</b>“你现在是生气，还是委屈？”“是不是有点失望？”孩子能说出情绪，情绪就小了一半。"),
        thing("<b>③ 给两个可接受的选择，而不是命令。</b>“你想现在收玩具，还是五分钟后收？”选择权给他，边界我守着——这是把控制变成合作的关键一招。", last=True),
    ])),
    p("情感引导不是一套话术，说到底是一种态度：我不急着纠正你，我先理解你；我不站在你对面，我蹲在你旁边。当孩子一次次确认“不管我什么样，爸都接得住”，他和你的那根线，就再也断不了了。"),
    p("这也是这本书名字的深意——孩子不需要最贵的玩具，他最想要的“玩具”，是那个愿意蹲下来、认认真真陪他、懂他情绪的你。"),
    p("最后一篇，我想聊聊我读这本书时最大的遗憾：它原本是写给 0 到 7 岁孩子父母的，而我儿子已经十五岁了。我想认真说一说——错过了所谓的“黄金期”，到底还来不来得及。"),
    companion(["孩子永远不会因为被吼而变懂事，", "只会因为被看见、被接住，", "而愿意慢慢向你打开。"]),
])
build("发布包_第6篇_情感引导五步法", "正文_第6篇_情感引导五步法.html",
      "孩子大吼大叫时，你第一句话最关键",
      ["孩子情绪上头的那一刻，", "你说的第一句话最关键"],
      "《你就是孩子最好的玩具》读书笔记 · 第 6 篇 · 共 7 篇｜情感引导五步法",
      body6)

# ============ 第 7 篇：回望 + 速览 ============
def recap_table():
    items = [
        ("情感引导", "不靠威逼利诱，教孩子认识、表达情绪，在平等关系里建立一生的亲密联结。"),
        ("误区一", "控制（“为你好”）养出讨好或反抗；放任则养出没边界的孩子。"),
        ("误区二", "否定感受（“不疼别哭”）→ 孩子闭嘴、情绪内耗。"),
        ("误区三", "外部奖励（德西效应）→ 奖走内在动力；要奖努力、慢奖、少交易。"),
        ("误区四", "消极惩罚 → 学会撒谎；改用“直接后果”，让行为自己长出结果。"),
        ("五步法", "提前告知 → 关注判断 → 认真聆听 → 体察理解 → 引导解决。"),
    ]
    tds=[]
    for i,(k,v) in enumerate(items):
        bg = C_LIGHT if i%2==0 else C_CARD
        tds.append(
            '<tr>'
            f'<td style="padding:9px 10px;font-weight:bold;border:1px solid {C_BORDER};background:{bg};white-space:nowrap;vertical-align:top;"><span style="color:{C_MAIN_D};">{k}</span></td>'
            f'<td style="padding:9px 10px;border:1px solid {C_BORDER};background:{bg};vertical-align:top;"><span style="color:{C_TXT};">{v}</span></td>'
            '</tr>')
    return f'''<table width="100%" style="width:100%;border-collapse:collapse;background:{C_LIGHT};border:1px solid {C_BORDER};margin:8px 0 16px;">
<tr><td style="padding:14px 16px 6px;">
<p style="margin:0 0 6px;font-size:15px;font-weight:bold;color:{C_MAIN_D};text-align:center;display:block;">《你就是孩子最好的玩具》· 一页速览</p>
</td></tr>
<tr><td style="padding:0 16px 16px;">
<table width="100%" style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.7;">
{''.join(tds)}
</table>
</td></tr>
</table>'''

body7 = "\n".join([
    p("读完这本书的那个晚上，我在沙发上坐了很久。"),
    p("书里反复提到，0 到 7 岁是情感引导的“黄金期”——孩子大脑里管情绪的部分正在飞速发育，这时候你给他多少倾听、回应和安全感，都像是在往银行里存钱，存够了，能吃一辈子。"),
    p("我转头看了看我儿子的房门。他今年十五岁，一米七五，声音变粗了，下巴上开始有绒毛。那个会摔跤了扑进我怀里哭、会奶声奶气喊爸爸的小不点，好像就在昨天，又好像已经很远了。"),
    p("说实话，我心里涌上一阵很浓的后悔：这本书，要是十年前就读到，该多好。"),
    book_intro("x",
        '<p style="margin:0 0 8px;font-size:16px;line-height:1.6;color:%s;font-weight:bold;text-align:center;display:block;">📖 读书笔记 ·《你就是孩子最好的玩具》第 7 篇（终篇）</p>'
        '<p style="margin:0;font-size:14px;line-height:1.8;color:#8a5a3a;text-align:left;">这一篇，我想写给和我一样“读到这本书时，孩子已经长大了”的父母。同时把前面六篇浓缩成一张速览，方便你收藏、也方便你转给身边正用得上的朋友。</p>' % C_MAIN_D),
    sub_head("错过了黄金期，就真的来不及了吗"),
    p("我带着这个遗憾又往下翻，慢慢松了一口气。金伯莉写这本书，重点虽然在幼年，但她从没说过“过了七岁就没戏了”。情感引导的本质——<b>看见情绪、接纳感受、平等对话</b>——对任何年龄的孩子都成立，对成年人也成立。"),
    p("而且我后来在王金海老师的课里听到一个特别安慰我的说法：青春期不是亲子关系的“末班车”，恰恰是第二个窗口期。小时候没存够的情感存款，青春期可以补；只是利息高一点、见效慢一点、你得更有耐心、更肯先低头而已。"),
    p("我自己这大半年的试，也验证了这件事。就从我少吼几句、多蹲下来听几句开始，那个把房门反锁的少年，门一点点开了。他会在我路过时忽然说一句学校的事，会在我递水过去时闷闷地说声“谢了”。这些瞬间小得不能再小，但我知道，那就是利息。"),
    golden(["最好的教育时机，", "一个是十年前，", "另一个，就是现在。"]),
    sub_head("一页速览（可直接收藏/转发）"),
    recap_table(),
    p("如果你时间有限，只记住三句话就够了："),
    things_card("".join([
        thing("<b>第一句：</b>情绪没有对错，行为才有边界。“你可以生气，但不能打人。”"),
        thing("<b>第二句：</b>先接住情绪，再讲道理。一个正在气头上的孩子，什么道理都听不进去。"),
        thing("<b>第三句：</b>孩子最想要的玩具，是蹲下来的你。陪伴的质量，不在于时间多长、玩具多贵，而在于你有没有真正“在场”。"),
    ])),
    sub_head("写在最后"),
    p("这本书的英文原名直译过来，叫《父母情感引导养育指南》。它不是教你怎么逗孩子玩，而是教你怎么和孩子的心，建立一条一辈子都断不了的线。"),
    p("我知道，读到这里的你，可能也正处在和孩子拧巴、较劲、说不上话的阶段。我想跟你说一句掏心窝子的话：<b>会后悔，就说明你在乎；愿意重新学，就永远不晚。</b>"),
    p("我也是个还在重启的爸爸，一路笨笨拙拙，破功比做到的时候多。但哪怕只是从今天起，少说一句“不哭”、多蹲下来一次、把一个命令换成一个选择——那扇门，就会松一条缝。"),
    companion(["这个系列到这里就结束了。", "愿我们都能成为孩子最好的“玩具”——", "那个他一回头，永远在、也永远懂他的人。", "门一直开着，他就敢走回来。"]),
], )
build("发布包_第7篇_多希望小时候读过", "正文_第7篇_多希望小时候读过.html",
      "多希望他小时候我就读过这本书，好在现在也不晚",
      ["多希望他小时候我就读过这本书", "好在，现在开始也不晚"],
      "《你就是孩子最好的玩具》读书笔记 · 第 7 篇 · 共 7 篇（终篇）｜回望与速览",
      body7)
