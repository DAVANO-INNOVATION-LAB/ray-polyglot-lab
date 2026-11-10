# SPDX-License-Identifier: Apache-2.0
"""Execute the exact guide sources and CLI in a fresh temporary directory."""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
page = root / "candidate/doc/source/core/examples/polyglot-batch.md"
blocks = re.findall(r"^```(\w+)\n(.*?)^```$", page.read_text(), re.M | re.S)
with tempfile.TemporaryDirectory(prefix="ray-polyglot-guide-") as temporary:
    source = Path(temporary)
    for language, filename in [
        ("cpp", "stats_worker.cpp"),
        ("java", "StatsWorker.java"),
        ("python", "polyglot_driver.py"),
    ]:
        matches = [content for tag, content in blocks if tag == language]
        assert len(matches) == 1
        (source / filename).write_text(matches[0])
    build = next(content for tag, content in blocks if tag == "bash" and "mktemp" in content)
    result = subprocess.run(
        ["bash", "-c", build], cwd=source, capture_output=True, text=True, check=True
    )
    bundle = result.stdout.strip()
    command = [sys.executable, str(source / "polyglot_driver.py"), "--bundle", bundle]
    direct = subprocess.run(
        [*command, "--direct"],
        cwd=source,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    print("DIRECT CLI:", direct.stdout, flush=True)
    expected = {"count": 4096, "sum": -2048, "sum_squares": 5726623744}
    assert json.loads(direct.stdout) == {"java": expected, "cpp": expected}
    distributed = subprocess.run(
        command, cwd=source, capture_output=True, text=True, check=True, timeout=180
    )
    print("RAY CLI:", distributed.stdout, flush=True)
    data = json.loads(distributed.stdout)
    assert data["verified"] is True
    assert data["task_count"] == 32
    assert data["totals"] == {"java": expected, "cpp": expected}
    assert data["worker_pids"] and data["node_ids"]
