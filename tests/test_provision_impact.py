from __future__ import annotations

import yaml

from scripts.provision_impact import set_status


def test_set_status_changes_only_the_named_facts(tmp_path) -> None:
    path = tmp_path / "policy.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "facts": [
                    {"id": "FACT-PROV-006", "status": "draft", "value": "a"},
                    {"id": "FACT-PROV-007", "status": "draft", "value": "b"},
                ]
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    assert set_status(tmp_path, ["FACT-PROV-007"], "approved") == 1
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))["facts"]
    assert [row["id"] for row in rows] == ["FACT-PROV-006", "FACT-PROV-007"]
    assert rows[0]["status"] == "draft"
    assert rows[1]["status"] == "approved"
