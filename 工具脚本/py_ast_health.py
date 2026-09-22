# -*- coding: utf-8 -*-
"""Python 脚本静态体检：找出「被调用但未定义」的名字（NameError 隐患）。

用途：改动较大的 .py（尤其是**用注释做替换边界、整段重写**之后）必须跑一次。
本脚本用 AST 静态分析，一次性列出所有未定义调用，不靠人工看函数列表。

用法：
  python 工具脚本/py_ast_health.py              # 检查 工具脚本/ 下全部 py
  python 工具脚本/py_ast_health.py 某文件.py     # 只检查指定文件

退出码：0 = 无隐患；1 = 发现隐患（可接提交前钩子）。

背景（真实事故 2026-09-22）：
  曾用「#---- dedupe」到「#---- CLI」两行注释作为替换边界，
  把夹在中间的 report() 整段删掉，导致**检测路径**抛 NameError。
  当时 --dry-run / --setup / --list-rules 三条路径都在到达 report 之前就
  return 了，所以三次手工测试全都没暴露；是另一个工具试跑**默认检测路径**
  才发现的。
  => 教训：**大段替换后不能只靠「跑通几条命令」，要做静态完整性检查。**
     而且测试必须覆盖**每条分支**，不能只测最短路径。
"""
import ast
import builtins
import io
import os
import sys

WS = r"D:\个人资料\家庭教育"
TOOLS = os.path.join(WS, "工具脚本")

if len(sys.argv) > 1:
    targets = [a if os.path.isabs(a) else os.path.join(TOOLS, a)
               for a in sys.argv[1:]]
else:
    targets = sorted(os.path.join(TOOLS, f) for f in os.listdir(TOOLS)
                     if f.endswith(".py"))

BUILTIN = set(dir(builtins))

print("=" * 76)
print("  Python 静态体检：被调用但未定义的名字（NameError 隐患）")
print("=" * 76)
print()

total_bad = 0
for p in targets:
    name = os.path.relpath(p, WS) if os.path.isabs(p) else p
    if not os.path.isfile(p):
        print("  (缺) %s" % name)
        continue
    src = io.open(p, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print("  ✗ %s 语法错误: %s" % (name, e))
        total_bad += 1
        continue

    # 收集模块级定义的函数/类/赋值名
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defined.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                defined.add((a.asname or a.name).split(".")[0])
    # 所有被赋值过的名字（含函数内局部变量、参数），保守起见都算"已定义"
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for a in (node.args.args + node.args.kwonlyargs
                      + node.args.posonlyargs):
                defined.add(a.arg)
            if node.args.vararg:
                defined.add(node.args.vararg.arg)
            if node.args.kwarg:
                defined.add(node.args.kwarg.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)
        elif isinstance(node, ast.comprehension):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    defined.add(t.id)
        elif isinstance(node, ast.Lambda):
            for a in (node.args.args + node.args.kwonlyargs
                      + node.args.posonlyargs):
                defined.add(a.arg)

    # 只查「形态像函数调用」的 Name
    called = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            n = node.func.id
            if n in BUILTIN:
                continue
            called.setdefault(n, node.lineno)

    missing = {k: v for k, v in called.items() if k not in defined}
    print("  %s" % name)
    print("     定义了 %d 个名字；检出 %d 个调用名，其中 %d 个未定义"
          % (len(defined), len(called), len(missing)))
    if missing:
        total_bad += len(missing)
        for k, ln in sorted(missing.items(), key=lambda x: x[1]):
            print("       ⛔ L%-4d %s()  ← 未定义" % (ln, k))
    else:
        print("       ✅ 无未定义调用")
    print()

print("=" * 76)
print("  合计隐患：%d 个" % total_bad)
print("=" * 76)
sys.exit(1 if total_bad else 0)
