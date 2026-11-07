"""Deterministic acceptance scoring for the private 512-question instrument.

The module scores a fixed question instrument end to end. It never ships the
instrument: the dataset and its document map live under the local data root,
while the public repository holds only the scoring code and thresholds.
"""

from .dataset import DatasetError, load_dataset, select_rows
from .docmap import DocMapError, load_docmap
from .runner import run_acceptance
from .scoring import aggregate, score_row

__all__ = [
    "DatasetError",
    "DocMapError",
    "aggregate",
    "load_dataset",
    "load_docmap",
    "run_acceptance",
    "score_row",
    "select_rows",
]
