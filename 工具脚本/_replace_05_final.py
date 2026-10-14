# -*- coding: utf-8 -*-
"""把已截好的临时片覆盖成 成片_05.mp4（处理 Windows 占用重试）。"""
import os
import shutil
import time

D = r"D:/个人资料/家庭教育/公众号/改善你的亲子关系/视频号文案/05_对同事客客气气回家只剩命令/_成品"
DST = os.path.join(D, "成片_05.mp4")
TMP = os.path.join(D, "成片_05.mp4.trimtmp.mp4")

assert os.path.exists(TMP), "临时片不存在"

last = None
for i in range(8):
    try:
        os.replace(TMP, DST)
        print("os.replace 成功")
        break
    except PermissionError as e:
        last = e
        print(f"第 {i+1} 次 os.replace 被拒，改用复制覆盖重试…")
        try:
            shutil.copy2(TMP, DST)
            os.remove(TMP)
            print("copy2 + remove 成功")
            break
        except PermissionError as e2:
            last = e2
            print(f"  copy2 也被拒：{e2}；等 1.5s")
            time.sleep(1.5)
else:
    raise SystemExit(f"始终无法覆盖，文件被占用：{last}")

print("最终文件：", DST, os.path.getsize(DST), "bytes")
