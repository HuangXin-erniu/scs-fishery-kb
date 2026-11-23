import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_ragas import _contexts, normalize_answer  # noqa: E402


def _chunk(doc_id, section, text):
    return SimpleNamespace(doc_id=doc_id, section=section, text=text)


def test_contexts_merge_all_chunks_in_section():
    chunks = [
        _chunk("DOC-1", "第八条", "第八条第一款"),
        _chunk("DOC-1", "第八条", "第八条第二款"),
        _chunk("DOC-2", "第一条", "其他"),
    ]
    service = SimpleNamespace(retriever=SimpleNamespace(chunks=chunks))
    result = SimpleNamespace(
        citations=[SimpleNamespace(doc_id="DOC-1", section="第八条", snippet="s")]
    )
    context = _contexts(service, result)
    assert "第八条第一款" in context
    assert "第八条第二款" in context
    assert "其他" not in context


def test_normalize_answer_strips_labels_question_and_gap():
    text = (
        "结论：没有捕捞许可证罚多少钱？：第八条 没收渔获物。 [DOC §第八条]\n"
        "缺口：本题问的是“没有捕捞许可证罚多少钱？”"
    )
    normalized = normalize_answer(text)
    assert "结论" not in normalized
    assert "没有捕捞许可证罚多少钱？" not in normalized
    assert "缺口" not in normalized
    assert "第八条 没收渔获物" in normalized
