from __future__ import annotations

import re

ARTICLE_RE = re.compile(r"^(第[一二三四五六七八九十百零〇]+条)(?:\s|$)")
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+、[^\n]{0,60})")
CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十]+章(?:\s|$)")
