from __future__ import annotations

import importlib.util
import json

from scs_fkb.config import REPO_ROOT


def _module():
    path = REPO_ROOT / "scripts" / "spot_check.py"
    spec = importlib.util.spec_from_file_location("spot_check", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dataset(path, *, per_stratum=14):
    rows = []
    for stratum in ("可答", "部分可答", "应拒答"):
        for index in range(per_stratum):
            rows.append(
                {
                    "id": f"{stratum}-{index:02d}",
                    "answerability": stratum,
                    "persona": ["船员", "船东", "基层执法", "基层推广"][index % 4],
                    "domain": "伏季休渔",
                    "dimension": "单点事实",
                    "question": f"问题 {stratum} {index}",
                    "scs_doc_ids": ["POL-CLOS-015"],
                }
            )
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8"
    )
    return rows


def test_sample_is_seeded_stratified_and_disjoint(tmp_path):
    module = _module()
    dataset = tmp_path / "dataset.jsonl"
    rows = _dataset(dataset)
    exclude_rows = [row for index, row in enumerate(rows) if index % 14 < 3]
    exclude = tmp_path / "exclude.ids"
    exclude.write_text("\n".join(row["id"] for row in exclude_rows) + "\n", encoding="utf-8")

    args = module.main(
        [
            "sample",
            "--dataset",
            str(dataset),
            "--out",
            str(tmp_path / "out"),
            "--seed",
            "7",
            "--exclude",
            str(exclude),
        ]
    )

    assert args == 0
    picked = (tmp_path / "out" / "sample.ids").read_text(encoding="utf-8").split()
    assert len(picked) == 30
    assert len(set(picked)) == 30
    assert not set(picked) & set(exclude.read_text(encoding="utf-8").split())
    report = json.loads((tmp_path / "out" / "sample.json").read_text(encoding="utf-8"))
    assert report["strata"] == {"可答": 10, "部分可答": 10, "应拒答": 10}
    assert report["disjoint_from_exclude"] is True
    assert set(report["personas"]) == {"船员", "船东", "基层执法", "基层推广"}

    again = module.main(
        [
            "sample",
            "--dataset",
            str(dataset),
            "--out",
            str(tmp_path / "out2"),
            "--seed",
            "7",
            "--exclude",
            str(exclude),
        ]
    )
    assert again == 0
    assert (tmp_path / "out2" / "sample.ids").read_text(encoding="utf-8") == (
        tmp_path / "out" / "sample.ids"
    ).read_text(encoding="utf-8")


def test_sample_refuses_a_stratum_that_is_too_small(tmp_path):
    module = _module()
    dataset = tmp_path / "dataset.jsonl"
    _dataset(dataset, per_stratum=3)
    code = module.main(
        ["sample", "--dataset", str(dataset), "--out", str(tmp_path / "out"), "--seed", "1"]
    )
    assert code != 0


def test_worksheet_has_the_judgement_columns_and_a_bom(tmp_path):
    module = _module()
    dataset = tmp_path / "dataset.jsonl"
    rows = _dataset(dataset)
    ids = tmp_path / "ids.txt"
    ids.write_text("\n".join(row["id"] for row in rows[:6]) + "\n", encoding="utf-8")

    assert (
        module.main(
            [
                "worksheet",
                "--dataset",
                str(dataset),
                "--ids",
                str(ids),
                "--out",
                str(tmp_path / "ws"),
            ]
        )
        == 0
    )

    raw = (tmp_path / "ws" / "worksheet.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    header = raw.decode("utf-8-sig").splitlines()[0].split(",")
    for column in module.JUDGEMENT_COLUMNS:
        assert column in header
    assert "expected_docs" in header
    assert len(raw.decode("utf-8-sig").splitlines()) == 7


def test_score_counts_yes_no_and_skips_na(tmp_path):
    module = _module()
    path = tmp_path / "filled.csv"
    lines = [
        "id,answerability,citation_ok,conclusion_ok,refusal_ok,asof_ok",
        "A-1,可答,Y,Y,NA,Y",
        "A-2,可答,Y,N,NA,NA",
        "A-3,可答,N,N,NA,NA",
        "A-4,部分可答,Y,Y,NA,Y",
        "R-1,应拒答,NA,NA,Y,NA",
        "R-2,应拒答,NA,NA,N,NA",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert module.main(["score", "--worksheet", str(path), "--out", str(tmp_path / "s")]) == 0
    result = json.loads((tmp_path / "s" / "scores.json").read_text(encoding="utf-8"))
    assert result["citation"] == {"hits": 3, "judged": 4, "rate": 0.75, "na": 0}
    assert result["conclusion"] == {"hits": 2, "judged": 4, "rate": 0.5, "na": 0}
    assert result["refusal"] == {"hits": 1, "judged": 2, "rate": 0.5, "na": 0}
    assert result["asof"] == {"hits": 2, "judged": 2, "rate": 1.0, "na": 4}
    assert result["citation_pass"] is False
    assert result["conclusion_pass"] is False
    assert result["refusal_pass"] is False
    assert result["unfilled"] == []
