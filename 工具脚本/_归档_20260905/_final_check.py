# -*- coding: utf-8 -*-
"""全量终检：所有正式正文跑 --check。"""
import os,subprocess
ROOT=r"D:/个人资料/家庭教育"
PY=r"C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
files=[]
for dp,dns,fns in os.walk(ROOT):
    p=dp.replace("\\","/")
    if "_backup" in p or "/.workbuddy" in p or "封面候选" in p: continue
    for fn in fns:
        if fn.endswith(".html") and fn.startswith("正文_") and "备份" not in fn and "预览" not in fn:
            files.append(os.path.join(dp,fn).replace("\\","/"))
files.sort()
r=subprocess.run([PY,os.path.join(ROOT,"wx_html_fix.py"),"--check"]+files,capture_output=True,text=True,encoding="utf-8")
print(r.stdout[-3000:])
