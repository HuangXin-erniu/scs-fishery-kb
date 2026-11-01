from __future__ import annotations

import re
from html.parser import HTMLParser

from ..patterns import ARTICLE_RE, CHAPTER_RE, SECTION_RE
from .base import Page, ParsedDocument, ParseError

BLOCK_TAGS = {
    "p",
    "div",
    "li",
    "td",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "blockquote",
}

NOISE_MARKERS = (
    "网站地图",
    "版权所有",
    "主办单位",
    "承办单位",
    "网站标识码",
    "公网安备",
    "ICP备",
    "ICP证",
    "无障碍",
    "设为首页",
    "收藏本站",
    "扫一扫",
    "打印本页",
    "关闭窗口",
    "相关稿件",
    "上一篇",
    "下一篇",
    "当前位置",
    "索引号",
    "信息名称",
    "发文机关",
    "成文日期",
    "发布日期",
    "浏览次数",
    "分享到",
    "访问分析",
    "网站纠错",
    "联系我们",
)

NOISE_EXACT = {
    "首页",
    "首页 首页",
    "简",
    "繁",
    "EN",
    "登录",
    "个人中心",
    "返回手机版",
    "国家规章库",
}


class _BlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.buffer: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript"):
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "br":
            self._flush()
            return
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            if self.skip:
                self.skip -= 1
            return
        if not self.skip and tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.buffer.append(data)

    def _flush(self) -> None:
        text = " ".join("".join(self.buffer).split())
        self.buffer = []
        if text:
            self.blocks.append(text)


def _blocks(html: str) -> list[str]:
    parser = _BlockParser()
    parser.feed(html)
    parser.close()
    parser._flush()
    return parser.blocks


def _is_noise(text: str) -> bool:
    if text in NOISE_EXACT:
        return True
    if any(marker in text for marker in NOISE_MARKERS):
        return True
    if len(text) <= 2 and not ARTICLE_RE.match(text) and not SECTION_RE.match(text):
        return True
    return False


def extract_main_text(html: str) -> str:
    """Extract the body of a legal/administrative page and drop site chrome."""
    blocks = [block for block in _blocks(html) if not _is_noise(block)]
    blocks = [block for block in blocks if not CHAPTER_RE.match(block)]

    article_positions = [index for index, block in enumerate(blocks) if ARTICLE_RE.match(block)]
    if article_positions:
        start = article_positions[0]
        end = article_positions[-1]
        return "\n".join(blocks[start : end + 1])

    section_positions = [index for index, block in enumerate(blocks) if SECTION_RE.match(block)]
    if section_positions:
        start = section_positions[0]
        end = len(blocks) - 1
        for index in range(len(blocks) - 1, start, -1):
            has_publisher = "农业农村部" in blocks[index]
            has_date = re.search(r"20\d{2}年\d{1,2}月\d{1,2}日", blocks[index])
            if has_publisher and has_date:
                end = index
                break
        return "\n".join(blocks[start : end + 1])

    return "\n".join(blocks)


def parse(path) -> ParsedDocument:
    raw = path.read_bytes()
    for encoding in ("utf-8", "gb18030"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ParseError(f"text.encoding: cannot decode {path.name}")

    body = extract_main_text(text)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        raise ParseError(f"text.empty: no body text in {path.name}")
    return ParsedDocument(pages=[Page(number=0, lines=lines)], parser="html.v1")
