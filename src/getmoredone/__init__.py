"""GetMoreDone - A Python task management application."""

# Kept in step with CHANGELOG.md's newest released heading by
# tests/test_version_source.py, which goes red if a release bumps one and not
# the other. A literal rather than a read of the changelog because the packaged
# app does not ship CHANGELOG.md -- tools/packaging_filters.py keeps repo-only
# files out of the bundle, and a runtime read would work from source and raise
# in the .app.
__version__ = "0.3.5"
