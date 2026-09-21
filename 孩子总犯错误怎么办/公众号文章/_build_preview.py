from pathlib import Path
import re
import base64
from html import escape

ROOT=Path(__file__).resolve().parent
def collect_paths():
    """兼容两种发布包结构：新结构「长图文发布包/正文_*.html」优先，回退包根。"""
    found=[]
    for folder in sorted(ROOT.glob('发布包_第*篇_*')):
        cands=list((folder/'长图文发布包').glob('正文_*.html')) or list(folder.glob('正文_*.html'))
        if not cands:
            continue
        num=int(re.search(r'第(\d+)篇',folder.name)[1])
        found.append((num,cands[0]))
    found.sort(key=lambda x:x[0])
    return [p for _,p in found]

def main():
    paths=collect_paths()
    bodies=[];buttons=[]
    for j,p in enumerate(paths):
        s=p.read_text(encoding='utf-8')
        b=re.search(r'<body[^>]*>(.*?)</body>',s,re.S)[1]
        covers=list(p.parent.glob('封面_*.jpg'))
        if covers:
            encoded=base64.b64encode(covers[0].read_bytes()).decode('ascii')
            b=f'<img alt="第{j+1}篇封面" src="data:image/jpeg;base64,{encoded}" style="display:block;width:100%;height:auto">'+b
        bodies.append(f'<section class="art{" show" if j==0 else ""}" id="art{j}">{b}</section>')
        buttons.append(f'<button type="button" onclick="show({j})" aria-label="查看第{j+1}篇">第{j+1}篇</button>')
    css='''*{box-sizing:border-box}body{margin:0;background:#E9ECE1;color:#35372F;font-family:"Microsoft YaHei",sans-serif}header{padding:20px 16px;text-align:center;background:#F8F9F4;border-bottom:1px solid #D3DAC5}h1{font-size:20px;margin:0 0 8px}header p{font-size:13px;margin:6px 0;line-height:1.7}button{border:1px solid #7A8065;border-radius:24px;background:#fff;color:#555D45;padding:9px 22px;margin:5px;cursor:pointer}button[aria-pressed="true"]{background:#555D45;color:white}main{max-width:640px;margin:20px auto}.art{display:none}.art.show{display:block}footer{text-align:center;padding:12px 8px 25px;position:sticky;bottom:0;background:#F8F9F4;border-top:1px solid #D3DAC5}button:disabled{opacity:.4;cursor:default}@media(max-width:480px){main{margin:0 auto}header{padding:14px 12px}}'''
    js=f'''let current=0;const total={len(paths)};function show(n){{current=Math.max(0,Math.min(total-1,n));document.querySelectorAll('.art').forEach((e,i)=>e.classList.toggle('show',i===current));document.querySelectorAll('nav button').forEach((e,i)=>e.setAttribute('aria-pressed',String(i===current)));document.getElementById('count').textContent='第 '+(current+1)+' 篇 / 共 '+total+' 篇';document.getElementById('prev').disabled=current===0;document.getElementById('next').disabled=current===total-1;window.scrollTo(0,0)}}document.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')show(current+1);if(e.key==='ArrowLeft')show(current-1)}});show(0);'''
    out=ROOT/'_预览';out.mkdir(exist_ok=True)
    page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>孩子又犯错以后 · 六篇全文预览</title><style>'+css+'</style></head><body><header><h1>孩子又犯错以后</h1><p>六篇正文已完成 · 橄榄绿配色</p><p>来源：扶鹰教育-王金海课程｜封面待制作</p><nav>'+''.join(buttons)+'</nav></header><main>'+''.join(bodies)+'</main><footer><p id="count"></p><button id="prev" onclick="show(current-1)">← 上一篇</button><button id="next" onclick="show(current+1)">下一篇 →</button></footer><script>'+js+'</script></body></html>'
    if all(list(p.parent.glob('封面_*.jpg')) for p in paths):
        page=page.replace('六篇正文已完成 · 橄榄绿配色','六篇正文与封面已完成 · 橄榄绿配色').replace('封面待制作','六套发布材料齐备')
    target=out/f'孩子总犯错误怎么办_全部正文预览_{len(paths)}篇.html';target.write_text(page,encoding='utf-8');print(target)

if __name__=='__main__':main()
