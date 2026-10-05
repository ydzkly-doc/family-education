"""从本系列正式发布包重建合并正文预览。"""

from pathlib import Path
import runpy

SERIES_DIR = Path(__file__).resolve().parent
WORKSPACE = SERIES_DIR.parents[2]
GENERATOR = WORKSPACE / "工具脚本" / "重建全部正文预览.py"

if __name__ == "__main__":
    build = runpy.run_path(str(GENERATOR))["build"]
    result = build(str(SERIES_DIR))
    if not result:
        raise SystemExit("未找到正式发布包正文")
    print(f"已重建：{result[0]}（{result[1]} 篇）")
