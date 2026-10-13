# -*- coding: utf-8 -*-
# 精修：版本行空格 + 录制提示金句版→常驻标题版口径。幂等。
import glob, re, sys
WRITE = "--write" in sys.argv
files=[f for f in glob.glob(r"D:/个人资料/家庭教育/公众号/手机方案/视频号文案_v4/[0-9]*/视频号文案_*.md") if "_长视频" not in f]
n_ver=n_tip=0
for f in files:
    s=open(f,encoding="utf-8").read(); o=s
    # 1 版本行去多余空格
    s2=re.sub(r"(- \*\*版本\*\*：)\s+常驻标题", r"\1常驻标题", s)
    if s2!=s: n_ver+=1
    s=s2
    # 2 录制提示：把“金句版”那句替换为常驻标题版口径
    def tip_repl(mm):
        rest=mm.group(0)
        # 抓强调句数量（“那 **N 句**”），用于保留信息
        nm=re.search(r"那\s*\*\*(\d+)\s*句\*\*", rest)
        cnt=nm.group(1) if nm else "几"
        return ("- 本条是**常驻标题版**：顶部一条全片常驻的主标题（**88 号白字雾蓝重点，后期叠加、不用念**）；"
                "底部上「三、上屏方案 → 强调句」里那 **%s 句**，结尾金句卡也改走底部。"
                "录制时这几句大致念到就行，别整句换成别的意思——锚点靠这几句定位。" % cnt)
    s2=re.sub(r"- 本条是\*\*金句版\*\*：[^\n]*", tip_repl, s)
    if s2!=s: n_tip+=1
    s=s2
    # 3 “开头钩子那句不用念”仍然成立（常驻版钩子也不用念），保留。
    if WRITE and s!=o: open(f,"w",encoding="utf-8").write(s)
print("文件数",len(f),"修版本行",n_ver,"修录制提示",n_tip,"模式",("WRITE" if WRITE else "DRY"))
