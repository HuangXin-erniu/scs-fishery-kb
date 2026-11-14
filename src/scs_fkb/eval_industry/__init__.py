"""Track B (industry-standard) evaluation dataset helpers.

The private instrument (512 questions) stays frozen and feeds Track A.  This
package builds and validates the separate Track B dataset used for RAGAS,
retrieval, citation and abstention metrics.  It never copies private questions
or gold answers into the repository.
"""

from __future__ import annotations

from .dataset import (
    FROZEN_CORE,
    SCHEMA_VERSION,
    SPLITS,
    build_dataset,
    load_rows,
    manifest,
    resolve_gold_docs,
    validate_rows,
    write_dataset,
)

__all__ = [
    "FROZEN_CORE",
    "SCHEMA_VERSION",
    "SPLITS",
    "build_dataset",
    "load_rows",
    "manifest",
    "resolve_gold_docs",
    "validate_rows",
    "write_dataset",
]
