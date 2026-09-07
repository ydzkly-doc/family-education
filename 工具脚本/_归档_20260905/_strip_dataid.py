# -*- coding: utf-8 -*-
"""剥离秀米/外部编辑器导出残留的 data-page-node-id 等 data-* 属性（微信粘贴会据此整段重置样式）。"""
import re, sys
for f in sys.argv[1:]:
    h=open(f,encoding="utf-8").read()
    before=h.count("data-page-node-id")
    # 删 data-page-node-id="xxx"（含前导空白）
    h2=re.sub(r'\s*data-page-node-id="[^"]*"','',h)
    # 兜底：删其它 data-page-* / data-* 编辑器残留（保留标准属性）
    h2=re.sub(r'\s*data-[a-zA-Z0-9\-]+="[^"]*"','',h2)
    after=h2.count("data-page-node-id")+len(re.findall(r'\s*data-[a-zA-Z0-9\-]+=',h2))
    open(f,"w",encoding="utf-8").write(h2)
    print(f"{f}\n  data-page-node-id {before}->0; 剩余data-*属性 {after}; len {len(h)}->{len(h2)}")
