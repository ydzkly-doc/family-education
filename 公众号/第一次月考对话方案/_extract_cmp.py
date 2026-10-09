import re, glob, os
base = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(base, "**", "正文_*.html"), recursive=True))
for f in files:
    html = open(f, encoding="utf-8").read()
    html = re.sub(r"</p>", "\n", html)
    txt = re.sub(r"<[^>]+>", "", html)
    txt = re.sub(r"[ \t]+", "", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    out = os.path.join(base, "_cmp_" + os.path.basename(f).replace(".html", ".txt"))
    open(out, "w", encoding="utf-8").write(txt)
    print(out, len(txt))
