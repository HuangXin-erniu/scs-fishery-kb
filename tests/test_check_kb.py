from __future__ import annotations

import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.models import Chunk


def _module():
    path = REPO_ROOT / "scripts" / "check_kb.py"
    spec = importlib.util.spec_from_file_location("check_kb", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _chunk() -> Chunk:
    text = "三、休渔时间 南海海域为5月1日12时至8月16日12时。"
    return Chunk(
        chunk_id="CH-1",
        doc_id="POL-CLOS-015",
        source_id="POL-CLOS-015",
        page=1,
        section="三、休渔时间",
        text=text,
        token_count=10,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        kind="corpus",
    )


def _files(tmp_path: Path, quote: str) -> tuple[Path, Path, Path]:
    data = tmp_path / "data"
    processed = data / "v2" / "processed"
    processed.mkdir(parents=True)
    (processed / "chunks.jsonl").write_text(
        json.dumps(asdict(_chunk()), ensure_ascii=False) + "\n", encoding="utf-8"
    )
    faq = tmp_path / "faq.yaml"
    faq.write_text(
        yaml.safe_dump(
            {
                "entries": [
                    {
                        "id": "FAQ-001",
                        "topic": "休渔",
                        "persona": "captain",
                        "question": "休渔时间？",
                        "answer": "5月1日12时至8月16日12时",
                        "citations": [
                            {
                                "doc": "POL-CLOS-015",
                                "section": "三、休渔时间",
                                "quote": quote,
                            }
                        ],
                    }
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    terms = tmp_path / "terms.yaml"
    terms.write_text(
        yaml.safe_dump(
            {
                "terms": [
                    {
                        "term_id": "TERM-001",
                        "official": "伏季休渔",
                        "plain": "每年固定一段时间禁止捕捞。",
                        "variants": ["休渔期"],
                        "citations": [{"doc": "POL-CLOS-015", "section": "三、休渔时间"}],
                    }
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return faq, terms, data


def test_check_kb_passes_a_verbatim_quote(tmp_path: Path, capsys) -> None:
    faq, terms, data = _files(tmp_path, "南海海域为5月1日12时至8月16日12时")
    module = _module()
    code = module.main(
        ["--data-root", str(data), "--faq", str(faq), "--terms", str(terms), "--json"]
    )
    capsys.readouterr()
    assert code == 0


def test_check_kb_fails_a_broken_quote(tmp_path: Path, capsys) -> None:
    faq, terms, data = _files(tmp_path, "这句话不在原文里")
    module = _module()
    code = module.main(
        ["--data-root", str(data), "--faq", str(faq), "--terms", str(terms), "--json"]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "quote not found" in captured.out
