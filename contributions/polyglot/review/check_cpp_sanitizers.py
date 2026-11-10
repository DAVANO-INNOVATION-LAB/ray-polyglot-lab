# SPDX-License-Identifier: Apache-2.0
"""Run deterministic C++ checks with AddressSanitizer and UndefinedBehaviorSanitizer."""

import json
import random
import re
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
page = root / "candidate/doc/source/core/examples/polyglot-batch.md"
blocks = re.findall(r"^```cpp\n(.*?)^```$", page.read_text(), re.M | re.S)
assert len(blocks) == 1
with tempfile.TemporaryDirectory(prefix="ray-polyglot-sanitizers-") as temporary:
    directory = Path(temporary)
    source = directory / "stats_worker.cpp"
    source.write_text(blocks[0])
    executable = directory / "stats_worker"
    subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-O1",
            "-g",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer",
            str(source),
            "-o",
            str(executable),
        ],
        check=True,
    )
    random_source = random.Random(51205)
    for case in range(60):
        values = [
            random_source.randint(-1000000, 1000000) for _ in range(random_source.randrange(4097))
        ]
        request = f"RAYPOLY1 {len(values)} " + " ".join(map(str, values)) + "\n"
        result = subprocess.run(
            [str(executable)], input=request.encode("ascii"), capture_output=True, timeout=5
        )
        assert result.returncode == 0, (case, result.stderr)
        assert not result.stderr, (case, result.stderr)
        reply = json.loads(result.stdout)
        assert reply == {
            "protocol": "RAYPOLY1",
            "language": "cpp",
            "count": len(values),
            "sum": sum(values),
            "sum_squares": sum(value * value for value in values),
        }
    for request in [
        b"",
        b"RAYPOLY1 -1",
        b"RAYPOLY1 4097",
        b"RAYPOLY1 1 9223372036854775808",
        b"RAYPOLY1 1 -9223372036854775809",
        b"x" * 65537,
        b"RAYPOLY1 1 \xff",
    ]:
        result = subprocess.run([str(executable)], input=request, capture_output=True, timeout=5)
        assert result.returncode == 2, (request[:50], result.returncode, result.stderr)
        assert result.stdout == b"", result.stdout
        assert result.stderr == b"invalid request\n", result.stderr
print("67 C++ sanitizer cases passed.")
