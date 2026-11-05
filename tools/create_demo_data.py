#!/usr/bin/env python3
"""Create demo data for GetMoreDone application.

This is primarily for dev/testing.

It inserts demo items into whichever DB is currently selected by GetMoreDone:
- explicit db path (if provided by caller)
- GETMOREDONE_DB env var
- GETMOREDONE_DATA_DIR env var (the whole data directory; the DB is
  <data dir>/getmoredone.db)
- otherwise the default per-OS Application Support location

This is the headless seed `start-demo.sh` runs on a demo instance's first
launch.

Spec:  docs/spec_2026-11-05_demo_install.md#d3
Tests: tests/test_demo_install.py::test_d3_create_demo_data_runs_against_an_isolated_db
"""

import sys
from pathlib import Path

# The repo's src/, not tools/src. This read `Path(__file__).parent / "src"`,
# which resolved to tools/src — a directory that does not exist — so run as a
# script, with sys.path[0] set to tools/, the import below failed outright.
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from getmoredone.demo_data import load_demo_data
from getmoredone.paths import resolve_db_path


def create_demo_data():
    target = resolve_db_path(None)
    print("Creating demo data for GetMoreDone...")
    print(f"Target database: {target}")
    created = load_demo_data(db_path=None)
    print(f"\nDemo data created successfully! ({created} items)")
    print("Run the application with: python run.py")


if __name__ == "__main__":
    create_demo_data()
