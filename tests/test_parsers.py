from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scs_fkb.parsers import parse_source
from scs_fkb.parsers.base import ParseError, UnsupportedFormatError

OFD_NS = "http://www.ofdspec.org/2016"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{WORD_NS}"><w:body>{body}</w:body></w:document>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def _write_ofd(path: Path, pages: dict[int, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for index, text in pages.items():
            content = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                f'<ofd:Page xmlns:ofd="{OFD_NS}"><ofd:Content><ofd:Layer>'
                "<ofd:TextObject><ofd:TextCode>" + text + "</ofd:TextCode></ofd:TextObject>"
                "</ofd:Layer></ofd:Content></ofd:Page>"
            )
            archive.writestr(f"Doc_0/Pages/Page_{index}/Content.xml", content)


def test_docx_paragraphs(tmp_path: Path) -> None:
    path = tmp_path / "doc.docx"
    _write_docx(path, ["中华人民共和国渔业法", "第一条 为了加强渔业资源的保护。", ""])
    parsed = parse_source(path, "docx")
    assert parsed.parser == "docx.v1"
    assert len(parsed.pages) == 1
    assert parsed.pages[0].number == 0
    assert parsed.pages[0].lines == ["中华人民共和国渔业法", "第一条 为了加强渔业资源的保护。"]


def test_docx_missing_document_part(tmp_path: Path) -> None:
    path = tmp_path / "empty.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/styles.xml", "<styles/>")
    with pytest.raises(ParseError, match="source.invalid_docx"):
        parse_source(path, "docx")


def test_docx_without_text_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "blank.docx"
    _write_docx(path, ["", "   "])
    with pytest.raises(ParseError, match="text.empty"):
        parse_source(path, "docx")


def test_ofd_pages_are_numeric(tmp_path: Path) -> None:
    path = tmp_path / "notice.ofd"
    _write_ofd(path, {0: "第一页内容。", 2: "第三页内容。", 10: "第十一页内容。"})
    parsed = parse_source(path, "ofd")
    assert parsed.parser == "ofd.v1"
    assert [page.number for page in parsed.pages] == [1, 3, 11]
    assert parsed.pages[0].text == "第一页内容。"
    assert parsed.pages[2].text == "第十一页内容。"


def test_ofd_without_pages_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.ofd"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("OFD.xml", "<ofd:OFD/>")
    with pytest.raises(ParseError, match="source.invalid_ofd"):
        parse_source(path, "ofd")


def test_unsupported_format(tmp_path: Path) -> None:
    path = tmp_path / "table.xlsx"
    path.write_bytes(b"PK")
    with pytest.raises(UnsupportedFormatError, match="source.unsupported_format"):
        parse_source(path, "xlsx")


def test_html_navigation_only_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "nav.html"
    path.write_text(
        "<html><body><div>网站地图</div><div>版权所有</div></body></html>",
        encoding="utf-8",
    )
    with pytest.raises(ParseError, match="text.empty"):
        parse_source(path, "html")


def test_html_keeps_articles(tmp_path: Path) -> None:
    path = tmp_path / "law.html"
    path.write_text(
        "<html><body><p>第一条 为了加强渔业资源的保护，制定本法。</p>"
        "<p>第二条 在中华人民共和国内水从事养殖，适用本法。</p></body></html>",
        encoding="utf-8",
    )
    parsed = parse_source(path, "html")
    assert parsed.pages[0].number == 0
    assert parsed.pages[0].lines[0].startswith("第一条")
