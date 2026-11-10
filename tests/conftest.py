import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def bundle():
    path = Path(os.environ.get("RAY_POLYGLOT_BUNDLE", ".build/bundle")).resolve()
    if not (path / "native/stats_worker").is_file():
        pytest.fail("Missing compiled workers: run python scripts/build.py before testing")
    return path
