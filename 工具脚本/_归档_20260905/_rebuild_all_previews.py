# -*- coding: utf-8 -*-
"""重建所有系列的「全部正文预览」单文件（本地校对用，不发布）。"""
import os,sys,importlib.util
ROOT=r"D:/个人资料/家庭教育"
spec=importlib.util.spec_from_file_location("bap",os.path.join(ROOT,"_build_all_previews.py"))
bap=importlib.util.module_from_spec(spec); spec.loader.exec_module(bap)

# 找所有含"公众号文章/发布包_*"的系列目录
series=[]
for dp,dns,fns in os.walk(ROOT):
    p=dp.replace("\\","/")
    if "_backup" in p or "/.workbuddy" in p: continue
    if os.path.basename(p)=="公众号文章":
        if any(d.startswith("发布包_") for d in dns):
            series_dir=os.path.dirname(p)
            name=os.path.basename(series_dir)
            series.append((series_dir,name))
series.sort(key=lambda x:x[1])
print(f"共 {len(series)} 个系列")
for sd,name in series:
    print("处理:",name)
    try:
        bap.build(sd,name)
    except Exception as e:
        print("  [ERR]",name,e)
