from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scs_fkb.eval_accept.dataset import DatasetError, load_dataset, select_rows
from scs_fkb.eval_accept.docmap import DocMap, DocMapError, load_docmap
from scs_fkb.eval_accept.points import ConceptSource, PointOverrides, PointSpec, derive_terms
from scs_fkb.eval_accept.report import write_metrics, write_report, write_rows_csv
from scs_fkb.eval_accept.runner import run_acceptance
from scs_fkb.eval_accept.scoring import (
    ScoringConfig,
    aggregate,
    gate_result,
    score_row,
)

ROOT = Path(__file__).resolve().parents[1]

MAPPING = {
    "SCS-N-001": {
        "title": "休渔通告",
        "docs": ["POL-CLOS-015"],
        "covers": "full",
    },
    "SCS-R-003": {
        "title": "捕捞许可管理规定",
        "docs": ["POL-STD-010"],
        "covers": "full",
    },
    "SCS-P-001": {
        "title": "广东休渔方案",
        "docs": ["POL-STD-010"],
        "covers": "partial",
    },
    "SCS-S-006": {"title": "海水水质标准", "docs": [], "covers": "missing"},
}


def make_row(**overrides):
    row = {
        "id": "Y-001",
        "split": "dev",
        "persona": "船员",
        "sea_area": "北部湾",
        "question": "今年休渔什么时候开始？",
        "domain": "伏季休渔",
        "domain_code": "KD-01",
        "answerability": "可答",
        "required_points": ["5月1日12时至8月16日12时"],
        "numeric_anchors": ["5月1日12时"],
        "dimension": "单点事实",
        "scs_doc_ids": ["SCS-N-001"],
        "citation_requirement": "SCS-N-001｜通告〔2023〕1号·休渔时间",
        "doc_locations": ["通告〔2023〕1号·休渔时间"],
    }
    row.update(overrides)
    return row


def make_result(answer: str, citations: list[dict] | None = None, **overrides):
    result = {
        "answer": answer,
        "citations": citations or [],
        "abstained": False,
        "reason": "ok",
        "mode": "kb_only",
        "latency_ms": 12,
    }
    result.update(overrides)
    return result


def make_docmap() -> DocMap:
    return DocMap.from_mapping(MAPPING)


def score(row, result, *, config: ScoringConfig | None = None):
    return score_row(
        row,
        result,
        docmap=make_docmap(),
        concepts=ConceptSource.load(ROOT / "configs" / "terms.yaml"),
        overrides=PointOverrides(),
        config=config or ScoringConfig(),
    )


def test_dataset_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    rows = [make_row(id="Y-001"), make_row(id="Y-002", answerability="应拒答")]
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    loaded = load_dataset(path)
    assert [row["id"] for row in loaded] == ["Y-001", "Y-002"]


def test_dataset_rejects_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(json.dumps(make_row()) + "\n" + json.dumps(make_row()) + "\n", encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(path)


def test_dataset_rejects_unknown_answerability(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(json.dumps(make_row(answerability="maybe")) + "\n", encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(path)


def test_select_rows_filters_in_order() -> None:
    rows = [
        make_row(id="Y-001", dimension="数值召回"),
        make_row(id="Y-002", dimension="单点事实"),
        make_row(id="Y-003", dimension="数值召回", split="holdout"),
    ]
    assert [row["id"] for row in select_rows(rows, dimension="数值召回")] == ["Y-001", "Y-003"]
    assert [row["id"] for row in select_rows(rows, split="dev", limit=1)] == ["Y-001"]


def test_docmap_two_way_resolution(tmp_path: Path) -> None:
    import yaml

    path = tmp_path / "doc-map.yaml"
    path.write_text(yaml.safe_dump({"mapping": MAPPING}, allow_unicode=True), encoding="utf-8")
    docmap = load_docmap(path)
    assert docmap.docs_for("SCS-N-001") == ("POL-CLOS-015",)
    assert docmap.scs_for_doc("POL-CLOS-015") == ("SCS-N-001",)
    assert docmap.covers("SCS-P-001") == "partial"
    assert docmap.covers("SCS-UNKNOWN") == "unknown"
    assert docmap.summary() == {
        "full": 2,
        "partial": 1,
        "missing": 1,
        "out_of_scope": 0,
        "total": 4,
    }


def test_docmap_rejects_missing_with_docs() -> None:
    with pytest.raises(DocMapError):
        DocMap.from_mapping({"SCS-X-001": {"docs": ["POL-LAW-009"], "covers": "missing"}})


def test_point_terms_prefer_numbers() -> None:
    concepts = ConceptSource.load(ROOT / "configs" / "terms.yaml")
    spec = derive_terms("南海带鱼肛长≥230毫米", concepts=concepts)
    assert "230毫米" in spec.terms
    assert spec.mode == "section"


def test_point_terms_use_concepts_and_flag_review() -> None:
    concepts = ConceptSource.load(ROOT / "configs" / "terms.yaml")
    spec = derive_terms("不得携带或使用禁用渔具", concepts=concepts)
    assert spec.terms
    review = derive_terms("区分全国通告与地方通告", concepts=concepts)
    assert review.terms == ()


def test_point_terms_honour_override() -> None:
    concepts = ConceptSource.load(ROOT / "configs" / "terms.yaml")
    override = PointOverrides(specs={("Y-001", 0): PointSpec(terms=("北部湾",), mode="document")})
    spec = derive_terms(
        "起止时间",
        concepts=concepts,
        override=override.get("Y-001", 0),
    )
    assert spec.terms == ("北部湾",)
    assert spec.mode == "document"


def test_scores_answerable_question() -> None:
    row = make_row()
    result = make_result(
        "5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]",
        [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
    )
    scored = score(row, result)
    assert scored["point_coverage"] == 1.0
    assert scored["citation_accuracy"] is True
    assert scored["band"] == 1.0


def test_scores_numeric_basis() -> None:
    row = make_row(dimension="数值召回", numeric_anchors=["5月1日12时"])
    without_basis = score(
        row,
        make_result(
            "5月1日12时起。 [POL-CLOS-015 §三、休渔时间]",
            [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
        ),
    )
    assert without_basis["basis_score"] == 0.5
    assert without_basis["band"] == 0.5
    with_basis = score(
        row,
        make_result(
            "按农业农村部通告〔2023〕1号，南海区为5月1日12时至8月16日12时。"
            " [POL-CLOS-015 §三、休渔时间]",
            [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
        ),
    )
    assert with_basis["basis_score"] == 1.0
    assert with_basis["band"] == 1.0


def test_scores_asof_for_time_conflicts() -> None:
    row = make_row(dimension="时效冲突", required_points=["起止时间"])
    undeclared = score(
        row,
        make_result(
            "5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]",
            [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
        ),
    )
    assert undeclared["asof_declared"] is False
    assert undeclared["band"] == 0.0
    declared = score(
        row,
        make_result(
            "按农业农村部通告〔2023〕1号，5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]",
            [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
        ),
    )
    assert declared["asof_declared"] is True


def test_refusal_scoring() -> None:
    row = make_row(answerability="应拒答", required_points=["专项品种"], scs_doc_ids=["SCS-S-006"])
    wrong = score(
        row,
        make_result(
            "可以罚款2000元。 [POL-STD-010 §第三十六条]",
            [{"doc_id": "POL-STD-010", "section": "第三十六条"}],
        ),
    )
    assert wrong["misanswer"] is True
    assert wrong["band"] == 0.0
    good = score(
        row,
        make_result("语料未收录该专项清单，无法给出具体船数；请咨询县级以上渔业主管部门。"),
    )
    assert good["misanswer"] is False
    assert good["correct_refusal"] is True
    assert good["band"] == 1.0


def test_refusal_without_channel_is_partial_credit() -> None:
    row = make_row(answerability="应拒答", required_points=["专项品种"], scs_doc_ids=["SCS-S-006"])
    scored = score(
        row,
        make_result("证据不足：未检索到相关依据。", abstained=True, reason="weak_evidence"),
    )
    assert scored["misanswer"] is False
    assert scored["correct_refusal"] is False
    assert scored["band"] == 0.5
    assert "refusal_without_channel" in scored["flags"]


def test_wrong_document_flags() -> None:
    row = make_row()
    scored = score(
        row,
        make_result(
            "与问题无关。 [POL-STD-010 §第三十六条]",
            [{"doc_id": "POL-STD-010", "section": "第三十六条"}],
        ),
    )
    assert scored["citation_accuracy"] is False
    assert "wrong_document" in scored["flags"]


def test_aggregate_and_gate() -> None:
    good = score(
        make_row(),
        make_result(
            "5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]",
            [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
        ),
    )
    metrics = aggregate([good])
    assert metrics["point_coverage"] == 1.0
    assert metrics["citation_accuracy"] == 1.0
    assert metrics["misanswer_rate"] is None
    gate = gate_result(metrics, ScoringConfig().thresholds)
    assert gate["passed"] is False
    assert any("misanswer_rate" in item for item in gate["failures"])


def test_gate_passes_when_limits_are_met() -> None:
    thresholds = {
        "misanswer_rate": 1.0,
        "citation_accuracy": 0.0,
        "point_coverage": 0.0,
        "refusal_channel_rate": 0.0,
        "asof_declaration_rate": 0.0,
        "basis_accuracy": 0.0,
    }
    metrics = {
        "misanswer_rate": 0.0,
        "citation_accuracy": 0.0,
        "point_coverage": 0.0,
        "refusal_channel_rate": 0.0,
        "asof_declaration_rate": 0.0,
        "basis_accuracy": 0.0,
    }
    assert gate_result(metrics, thresholds)["passed"] is True


class FakeService:
    def __init__(self, results=None, fail_on=None):
        self.results = results or {}
        self.fail_on = fail_on
        self.seen: list[str] = []

    def query(self, question, web="off"):
        self.seen.append(question)
        if self.fail_on and self.fail_on in question:
            raise RuntimeError("service down")
        payload = self.results.get(question, {"answer": "证据不足。", "abstained": True})
        return SimpleNamespace(
            answer=payload.get("answer", ""),
            citations=payload.get("citations", []),
            abstained=payload.get("abstained", False),
            reason=payload.get("reason", "ok"),
            mode=payload.get("mode", "kb_only"),
            latency_ms=payload.get("latency_ms", 5),
        )


def test_runner_records_failures_per_question() -> None:
    rows = [make_row(id="Y-001"), make_row(id="Y-002", question="会失败的问题")]
    service = FakeService(fail_on="会失败")
    scored = run_acceptance(
        rows,
        service,
        docmap=make_docmap(),
        concepts=ConceptSource.load(ROOT / "configs" / "terms.yaml"),
        overrides=PointOverrides(),
        config=ScoringConfig(),
    )
    assert scored[1]["reason"] == "runner_error"
    assert "service down" in scored[1]["error"]


def test_report_writers(tmp_path: Path) -> None:
    scored = [
        score(
            make_row(),
            make_result(
                "5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]",
                [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
            ),
        )
    ]
    overall = aggregate(scored)
    gate = gate_result(overall, ScoringConfig().thresholds)
    from scs_fkb.eval_accept.scoring import group_metrics, latency_summary, reason_clusters

    write_rows_csv(scored, tmp_path / "rows.csv")
    assert "citation_accuracy" in (tmp_path / "rows.csv").read_text(encoding="utf-8")
    write_report(
        path=tmp_path / "baseline.md",
        arm="extractive",
        rows=len(scored),
        overall=overall,
        groups=group_metrics(scored),
        gate=gate,
        clusters=reason_clusters(scored),
        latency=latency_summary(scored),
        failures=[],
    )
    report = (tmp_path / "baseline.md").read_text(encoding="utf-8")
    assert "point_coverage" in report and "Gate passed: False" in report
    write_metrics({"overall": overall}, tmp_path / "metrics.json")
    assert json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))["overall"]


def test_importer_is_deterministic(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "import_eval_xlsx", ROOT / "scripts" / "import_eval_xlsx.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    workbook = openpyxl.Workbook()
    questions = workbook.active
    questions.title = "验收集"
    questions.append(module.QUESTION_HEADERS)
    questions.append(
        [
            "Y-001",
            "船员",
            "拖网船长",
            "北部湾",
            "休渔前",
            "今年休渔什么时候开始？",
            "确认时间",
            "伏季休渔",
            "政策法规",
            "可答",
            "时间",
            "5月1日12时起",
            "SCS-N-001",
            "休渔时间",
            "易",
            "单点事实",
            "无",
        ]
    )
    grading = workbook.create_sheet("判分要点")
    grading.append(module.POINT_HEADERS)
    grading.append(
        [
            "Y-001",
            "单点事实",
            "可答",
            "①5月1日12时开始",
            "5月1日12时",
            "未声明",
            "SCS-N-001｜休渔时间",
            "要点齐",
            "编造",
        ]
    )
    domains = workbook.create_sheet("知识域体系")
    domains.append(module.DOMAIN_HEADERS)
    domains.append(["KD-01", "伏季休渔", "休渔时间", "1", "SCS-N-001", ""])
    xlsx = tmp_path / "instrument.xlsx"
    workbook.save(xlsx)

    first = module.import_workbook(xlsx, tmp_path / "first")
    second = module.import_workbook(xlsx, tmp_path / "second")
    assert first["dataset"]["sha256"] == second["dataset"]["sha256"]
    assert first["dataset"]["rows"] == 1
    row = json.loads((tmp_path / "first" / "dataset.jsonl").read_text(encoding="utf-8"))
    assert row["id"] == "Y-001"
    assert row["required_points"] == ["5月1日12时开始"]
    assert row["numeric_anchors"] == ["5月1日12时"]
    assert row["scs_doc_ids"] == ["SCS-N-001"]
    assert row["domain_code"] == "KD-01"
    assert row["split"] in {"dev", "holdout"}


def test_importer_rejects_missing_sheet(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "import_eval_xlsx_missing", ROOT / "scripts" / "import_eval_xlsx.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    workbook = openpyxl.Workbook()
    workbook.active.title = "验收集"
    xlsx = tmp_path / "broken.xlsx"
    workbook.save(xlsx)
    with pytest.raises(ValueError):
        module.import_workbook(xlsx, tmp_path / "out")


def test_split_assignment_is_balanced() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "import_eval_xlsx_split", ROOT / "scripts" / "import_eval_xlsx.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ids = [f"Y-{index:03d}" for index in range(1, 301)]
    assignment = module._split_assignment(ids, "seed")
    assert sum(1 for value in assignment.values() if value == "dev") == 256
    assert sum(1 for value in assignment.values() if value == "holdout") == 44


def test_location_tokens_strip_document_numbers() -> None:
    from scs_fkb.eval_accept.scoring import _location_tokens

    tokens = _location_tokens("通告〔2023〕1号·休渔海域与时间")
    assert "休渔海域" in tokens or "休渔" in tokens
    assert "时间" in tokens
    assert not any("〔" in token for token in tokens)


def test_page_or_table_hit() -> None:
    from scs_fkb.eval_accept.scoring import _page_or_table_hit

    citation = {"doc_id": "POL-TEST", "page": 3, "section": "表1 最小网目"}
    assert _page_or_table_hit("表1", citation, "表1最小网目") is True
    assert _page_or_table_hit("第3页", citation, "") is True
    assert _page_or_table_hit("表2", citation, "表1最小网目") is False


def test_typed_rule_scores_a_time_point() -> None:
    row = make_row(required_points=["起止时间"], numeric_anchors=[], dimension="单点事实")
    scored = score(
        row,
        make_result(
            "5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]",
            [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
        ),
    )
    assert scored["points_judgeable"] == 1
    assert scored["point_coverage"] == 1.0


def test_typed_rule_needs_cited_text() -> None:
    row = make_row(required_points=["起止时间"], numeric_anchors=[], dimension="单点事实")
    scored = score(row, make_result("5月1日至8月16日。", []))
    assert scored["points_judgeable"] == 1
    assert scored["point_coverage"] == 0.0


def test_grounded_override_replaces_unanchored_point(tmp_path: Path) -> None:
    row = make_row(required_points=["逾期处理"], numeric_anchors=[], dimension="单点事实")
    result = make_result(
        "逾期未改正的，责令改正。 [POL-CLOS-015 §三、休渔时间]",
        [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
    )
    without = score(row, result)
    assert without["point_coverage"] is None
    overrides = PointOverrides(specs={("Y-001", 0): PointSpec(terms=("责令改正",), mode="section")})
    with_override = score_row(
        row,
        result,
        docmap=make_docmap(),
        concepts=ConceptSource.load(ROOT / "configs" / "terms.yaml"),
        overrides=overrides,
        config=ScoringConfig(),
    )
    assert with_override["point_coverage"] == 1.0


def test_point_coverage_excludes_refusal_rows() -> None:
    answerable = make_row(id="Y-100", answerability="可答")
    refusal = make_row(id="Y-101", answerability="应拒答")
    scored = [
        score(
            answerable,
            make_result(
                "5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]",
                [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
            ),
        ),
        score(refusal, make_result("", [])),
    ]
    summary = aggregate(scored)
    assert summary["point_coverage"] == 1.0
    assert summary["point_coverage_all"] == 0.5
    assert summary["point_rows"] == 1
    assert summary["point_rows_all"] == 2


def test_v2_locates_a_citation_at_document_level() -> None:
    row = make_row(citation_requirement="SCS-N-001｜通告〔2023〕1号·休渔时间")
    result = make_result(
        "自2023年4月15日起施行。 [POL-CLOS-015 §四、实施时间]",
        citations=[
            {
                "doc_id": "POL-CLOS-015",
                "section": "四、实施时间",
                "snippet": "自2023年4月15日起施行。",
                "page": 1,
            }
        ],
    )
    v1 = score(row, result)
    v2 = score(row, result, config=ScoringConfig(protocol="v2"))
    assert v1["citation_accuracy"] is False
    assert v2["citation_accuracy"] is True
    assert v2["citation_location_source"] == "document"


def test_v2_partial_point_coverage_requires_half_with_a_two_term_minimum() -> None:
    from scs_fkb.eval_accept.scoring import _point_covered

    citations = [
        {
            "doc_id": "POL-CLOS-015",
            "section": "三、休渔时间",
            "snippet": "甲项乙项。",
            "page": 1,
        }
    ]
    answer = "甲项乙项。 [POL-CLOS-015 §三、休渔时间]"
    three = PointSpec(terms=("甲项", "乙项", "丙项"), mode="section")
    two = PointSpec(terms=("甲项", "丙项"), mode="section")
    assert _point_covered(answer, citations, three, ScoringConfig()) is False
    assert _point_covered(answer, citations, three, ScoringConfig(protocol="v2")) is True
    assert _point_covered(answer, citations, two, ScoringConfig(protocol="v2")) is False


def test_v2_basis_excludes_refusal_rows_and_accepts_one_anchor() -> None:
    refusal = make_row(
        id="Y-900",
        answerability="应拒答",
        dimension="数值召回",
        numeric_anchors=["2025年"],
    )
    refusal_result = make_result("2025年度公报未收录该指标。")
    v1_refusal = score(refusal, refusal_result)
    v2_refusal = score(refusal, refusal_result, config=ScoringConfig(protocol="v2"))
    assert v1_refusal["basis_score"] == 1.0
    assert v2_refusal["basis_score"] is None

    answered = make_row(
        id="Y-901",
        dimension="数值召回",
        numeric_anchors=["230毫米", "150毫米"],
    )
    answered_result = make_result("230毫米，表列值。 [POL-CLOS-015 §第三条]")
    v1 = score(answered, answered_result)
    v2 = score(answered, answered_result, config=ScoringConfig(protocol="v2"))
    assert v1["basis_score"] == 0.0
    assert v2["basis_score"] == 1.0
