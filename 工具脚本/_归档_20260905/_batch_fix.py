# -*- coding: utf-8 -*-
"""批量：收集所有正式正文(正文_*.html，排除说教版备份)，备份后跑 wx_html_fix 流水线。"""
import os,re,subprocess,sys,shutil
ROOT=r"D:/个人资料/家庭教育"
PY=r"C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
BK=os.path.join(ROOT,"_backup_微信规范化批量_20260904")
os.makedirs(BK,exist_ok=True)

files=[]
for dp,dns,fns in os.walk(ROOT):
    p=dp.replace("\\","/")
    if "_backup" in p or "/.workbuddy" in p or "封面候选" in p:
        continue
    for fn in fns:
        if fn.endswith(".html") and fn.startswith("正文_") and "备份" not in fn and "预览" not in fn:
            files.append(os.path.join(dp,fn).replace("\\","/"))
files.sort()
print(f"共 {len(files)} 篇正式正文")

# 备份（保留系列相对路径）
for f in files:
    rel=f[len(ROOT)+1:]
    dst=os.path.join(BK,rel).replace("\\","/")
    os.makedirs(os.path.dirname(dst),exist_ok=True)
    shutil.copy2(f,dst)
print("已备份到",BK)

# 调流水线
r=subprocess.run([PY,os.path.join(ROOT,"wx_html_fix.py")]+files,capture_output=True,text=True,encoding="utf-8")
print(r.stdout)
if r.stderr: print("STDERR:",r.stderr[:2000])
