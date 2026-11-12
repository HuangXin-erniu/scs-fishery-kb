from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "discover_candidates", ROOT / "scripts" / "discover_candidates.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_links_keeps_same_site_keyword_links() -> None:
    html = """
    <html><body>
      <a href="/notice/2026/taifeng.html">2026年台风预警通知</a>
      <a href="https://other.example.org/休渔">休渔</a>
      <a href="/images/a.jpg">休渔图片</a>
      <a href="/other/contact.html">联系我们</a>
      <a href="/notice/2026/xiuyu.html">南海伏季休渔实施方案</a>
    </body></html>
    """
    rows = _module().extract_links(html, "https://www.example.gov.cn/")
    urls = [row["url"] for row in rows]
    assert "https://www.example.gov.cn/notice/2026/taifeng.html" in urls
    assert "https://www.example.gov.cn/notice/2026/xiuyu.html" in urls
    assert all("other.example.org" not in url for url in urls)
    assert all(not url.endswith(".jpg") for url in urls)
    assert all(row["score"] > 0 for row in rows)


def test_extract_links_limit_and_dedup() -> None:
    html = "".join(f'<a href="/n/{index}.html">休渔通知 {index}</a>' for index in range(10))
    rows = _module().extract_links(html, "https://example.gov.cn/", limit=3)
    assert len(rows) == 3
    assert len({row["url"] for row in rows}) == 3
