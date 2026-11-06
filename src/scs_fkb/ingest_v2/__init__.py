"""Parallel ingestion v2.

The v1 ``scs_fkb.ingest`` module stays the default until the new index and
answer path are accepted. This package builds snapshots, parent/child chunks and
an incremental manifest without changing the live store.
"""

from .pipeline import BuildResult, IngestV2Error, build_v2
from .snapshot import SnapshotError, snapshot_registry

__all__ = [
    "BuildResult",
    "IngestV2Error",
    "SnapshotError",
    "build_v2",
    "snapshot_registry",
]
