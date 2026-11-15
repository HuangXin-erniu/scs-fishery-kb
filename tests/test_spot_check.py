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


def test_worksheet_merges_the_summary_and_its_provenance(tmp_path):
    module = _module()
    dataset = tmp_path / "dataset.jsonl"
    rows = _dataset(dataset)
    ids = tmp_path / "ids.txt"
    ids.write_text("\n".join(row["id"] for row in rows[:3]) + "\n", encoding="utf-8")
    answers = tmp_path / "answers.jsonl"
    answers.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": row["id"],
                    "summary": f"结论：{row['id']} 的摘要 [POL-CLOS-015 §三]",
                    "summary_source": "model" if index else "fallback",
                },
                ensure_ascii=False,
            )
            for index, row in enumerate(rows[:3])
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        module.main(
            [
                "worksheet",
                "--dataset",
                str(dataset),
                "--ids",
                str(ids),
                "--answers",
                str(answers),
                "--out",
                str(tmp_path / "ws"),
            ]
        )
        == 0
    )

    header = (tmp_path / "ws" / "worksheet.csv").read_bytes().decode("utf-8-sig").splitlines()[0]
    assert "summary" in header.split(",")
    assert "summary_source" in header.split(",")
    text = (tmp_path / "ws" / "worksheet.csv").read_bytes().decode("utf-8-sig")
    assert "的摘要" in text
    assert "fallback" in text


def test_worksheet_refuses_to_silently_drop_a_row_without_an_answer(tmp_path):
    module = _module()
    dataset = tmp_path / "dataset.jsonl"
    rows = _dataset(dataset)
    ids = tmp_path / "ids.txt"
    ids.write_text("\n".join(row["id"] for row in rows[:2]) + "\n", encoding="utf-8")
    answers = tmp_path / "answers.jsonl"
    answers.write_text(
        json.dumps({"id": rows[0]["id"], "summary": "x", "summary_source": "model"}) + "\n",
        encoding="utf-8",
    )
    code = module.main(
        [
            "worksheet",
            "--dataset",
            str(dataset),
            "--ids",
            str(ids),
            "--answers",
            str(answers),
            "--out",
            str(tmp_path / "ws"),
        ]
    )
    assert code != 0


def test_score_reports_the_fallback_rate(tmp_path):
    module = _module()
    path = tmp_path / "filled.csv"
    lines = [
        "id,answerability,summary_source,citation_ok,conclusion_ok,refusal_ok,asof_ok",
        "A-1,可答,model,Y,Y,NA,NA",
        "A-2,可答,fallback,Y,N,NA,NA",
        "A-3,可答,model,N,N,NA,NA",
        "A-4,部分可答,model,Y,Y,NA,NA",
        "R-1,应拒答,model,NA,NA,Y,NA",
        "R-2,应拒答,model,NA,NA,Y,NA",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert module.main(["score", "--worksheet", str(path), "--out", str(tmp_path / "s")]) == 0
    result = json.loads((tmp_path / "s" / "scores.json").read_text(encoding="utf-8"))
    assert result["summary_source"] == {"model": 5, "fallback": 1}
    assert result["fallback_rows"] == ["A-2"]
    assert result["fallback_rate"] == round(1 / 6, 4)


def test_worksheet_resolves_instrument_document_ids_through_the_doc_map(tmp_path):
    module = _module()
    dataset = tmp_path / "dataset.jsonl"
    rows = _dataset(dataset)
    ids = tmp_path / "ids.txt"
    ids.write_text(rows[0]["id"] + "\n", encoding="utf-8")
    doc_map = tmp_path / "doc-map.yaml"
    doc_map.write_text(
        "mapping:\n"
        "  SCS-L-002:\n"
        "    title: 海上交通安全法\n"
        "    registry_status: 已核验\n"
        "    docs: [POL-LAW-097]\n"
        "    covers: full\n",
        encoding="utf-8",
    )
    # Rewrite the row so its expected document is the instrument id, not a doc id.
    row = dict(rows[0])
    row["scs_doc_ids"] = ["SCS-L-002"]
    dataset.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    assert (
        module.main(
            [
                "worksheet",
                "--dataset",
                str(dataset),
                "--ids",
                str(ids),
                "--doc-map",
                str(doc_map),
                "--out",
                str(tmp_path / "ws"),
            ]
        )
        == 0
    )
    text = (tmp_path / "ws" / "worksheet.csv").read_bytes().decode("utf-8-sig")
    assert "海上交通安全法" in text
    assert "POL-LAW-097" in text
