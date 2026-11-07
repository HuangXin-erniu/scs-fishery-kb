from __future__ import annotations

import re

OUT_OF_SCOPE = re.compile(
    r"西沙|南沙|三沙|中沙|曾母暗沙|境外|公海|外国籍|台湾|香港|澳门|越南|菲律宾|马来西亚|印尼|越界|抓扣"
)


def out_of_scope(question: str) -> tuple[bool, str]:
    """Return whether a question sits outside the nearshore scope and why."""
    match = OUT_OF_SCOPE.search(question)
    if not match:
        return False, ""
    return True, f"问题涉及{match.group(0)}，超出南海北部近海知识库范围"
