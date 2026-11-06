"""Deterministic v2 evaluation: 120 questions and RAGAS-compatible metrics."""

from .metrics import (
    METRIC_NAMES,
    aggregate,
    answer_correctness,
    citation_resolution,
    gate_ok,
    score_row,
)
from .runner import THRESHOLDS, load_questions, run_eval, write_report

__all__ = [
    "METRIC_NAMES",
    "THRESHOLDS",
    "aggregate",
    "answer_correctness",
    "citation_resolution",
    "gate_ok",
    "load_questions",
    "run_eval",
    "score_row",
    "write_report",
]
