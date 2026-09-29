from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "_预览" / "我们到底在吵什么_五篇正文审阅版.pdf"
FONT_REGULAR = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def parse_style(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in value.split(";"):
        if ":" in part:
            key, item = part.split(":", 1)
            result[key.strip().lower()] = item.strip()
    return result


def parse_px(value: str | None, default: float) -> float:
    if not value:
        return default
    match = re.search(r"[\d.]+", value)
    return float(match.group()) if match else default


def parse_color(value: str | None, default: colors.Color) -> colors.Color:
    if not value:
        return default
    try:
        return colors.HexColor(value)
    except ValueError:
        return default


@dataclass
class TextBlock:
    text: str
    style: dict[str, str]
    section_styles: list[dict[str, str]]


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section_stack: list[dict[str, str]] = []
        self.in_paragraph = False
        self.paragraph_style: dict[str, str] = {}
        self.paragraph_sections: list[dict[str, str]] = []
        self.parts: list[str] = []
        self.blocks: list[TextBlock] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "section":
            self.section_stack.append(parse_style(attr_map.get("style") or ""))
        elif tag == "p":
            self.in_paragraph = True
            self.paragraph_style = parse_style(attr_map.get("style") or "")
            self.paragraph_sections = [item.copy() for item in self.section_stack]
            self.parts = []
        elif tag == "br" and self.in_paragraph:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self.in_paragraph:
            text = "".join(self.parts).strip()
            if text:
                self.blocks.append(TextBlock(text, self.paragraph_style, self.paragraph_sections))
            self.in_paragraph = False
        elif tag == "section" and self.section_stack:
            self.section_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.in_paragraph:
            self.parts.append(data)


def nearest_background(block: TextBlock) -> str | None:
    for style in reversed(block.section_styles):
        if "background" in style:
            return style["background"]
    return None


def make_paragraph(block: TextBlock, index: int) -> Paragraph:
    source_size = parse_px(block.style.get("font-size"), 16)
    size = min(19, max(9, source_size * 0.78))
    centered = block.style.get("text-align") == "center"
    bold = block.style.get("font-weight") == "bold"
    foreground = parse_color(block.style.get("color"), colors.HexColor("#34383B"))
    background_value = nearest_background(block)
    background = parse_color(background_value, colors.white) if background_value else None
    is_dark_header = background_value and background_value.upper() == "#46535E"
    is_heading = source_size >= 19 or bold

    style = ParagraphStyle(
        name=f"block-{index}",
        fontName="MicrosoftYaHeiBold" if bold else "MicrosoftYaHei",
        fontSize=size,
        leading=size * (1.55 if is_heading else 1.72),
        textColor=foreground,
        alignment=TA_CENTER if centered else TA_LEFT,
        spaceBefore=5 if is_heading else 1,
        spaceAfter=7 if is_heading else 5,
        backColor=background,
        borderPadding=(5, 8, 5, 8) if background and background != colors.white else 0,
        borderRadius=4,
        allowWidows=0,
        allowOrphans=0,
    )
    if is_dark_header:
        style.spaceBefore = 0
        style.spaceAfter = 0
        style.borderPadding = (6, 10, 6, 10)
    text = escape(block.text).replace("\n", "<br/>")
    return Paragraph(text, style)


def footer(canvas, document) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#D8D0C6"))
    canvas.line(20 * mm, 13 * mm, width - 20 * mm, 13 * mm)
    canvas.setFont("MicrosoftYaHei", 8.5)
    canvas.setFillColor(colors.HexColor("#70757A"))
    canvas.drawString(20 * mm, 8.5 * mm, "我们到底在吵什么 · 五篇正文审阅版")
    canvas.drawRightString(width - 20 * mm, 8.5 * mm, f"第 {document.page} 页")
    canvas.restoreState()


def main() -> None:
    pdfmetrics.registerFont(TTFont("MicrosoftYaHei", str(FONT_REGULAR), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("MicrosoftYaHeiBold", str(FONT_BOLD), subfontIndex=0))

    inputs = [
        ROOT / "样板_第1篇_炒面争吵" / "正文_第1篇_炒面争吵.html",
        ROOT / "样板_第2篇_先听后解" / "正文_第2篇_先听后解.html",
        ROOT / "正文稿_第3篇_袜子争吵" / "正文_第3篇_袜子争吵.html",
        ROOT / "正文稿_第4篇_生日蛋糕" / "正文_第4篇_生日蛋糕.html",
        ROOT / "正文稿_第5篇_气质标签" / "正文_第5篇_气质标签.html",
    ]
    story = []
    for article_index, path in enumerate(inputs):
        parser = ArticleParser()
        parser.feed(path.read_text(encoding="utf-8"))
        if not parser.blocks:
            raise ValueError(f"未提取到正文：{path}")
        if article_index:
            story.append(PageBreak())
        for block_index, block in enumerate(parser.blocks):
            story.append(make_paragraph(block, article_index * 1000 + block_index))
            if parse_px(block.style.get("font-size"), 16) >= 19:
                story.append(Spacer(1, 2.5 * mm))

    OUTPUT.parent.mkdir(exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=17 * mm,
        bottomMargin=18 * mm,
        title="我们到底在吵什么 - 五篇正文审阅版",
        author="归途有光·和孩子一起重启",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
