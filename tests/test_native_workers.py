import random
import shutil
import subprocess

import pytest

from ray_polyglot.protocol import expected
from ray_polyglot.runner import run_native


@pytest.mark.parametrize("language", ["java", "cpp"])
@pytest.mark.parametrize("values", [[], [0], [-1, 2, -3], [1000000] * 4096, [-1000000] * 4096])
def test_compiled_worker(language, values, bundle):
    result = run_native(language, values, bundle=bundle)
    assert {key: result[key] for key in expected(values)} == expected(values)


def test_deterministic_randomized_parity(bundle):
    rng = random.Random(99)
    for size in (1, 7, 100, 1024, 4096):
        values = [rng.randint(-1000000, 1000000) for _ in range(size)]
        for language in ("java", "cpp"):
            result = run_native(language, values, bundle=bundle)
            assert {key: result[key] for key in expected(values)} == expected(values)


@pytest.mark.parametrize("language", ["java", "cpp"])
@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"RAYPOLY1",
        b"RAYPOLY1 -1",
        b"RAYPOLY1 4097",
        b"RAYPOLY1 1",
        b"RAYPOLY1 0 1",
        b"RAYPOLY1 1 1.5",
        b"RAYPOLY1 1 1000001",
        b"RAYPOLY1 1 -1000001",
        b"RAYPOLY1 1 999999999999999999999",
        b"RAYPOLY1 1 +1",
        b"RAYPOLY1 1 01",
        b"RAYPOLY1 1 \xff",
        b"RAYPOLY1 1 1\x00",
        b"x" * 65537,
    ],
)
def test_malformed_native_input(language, payload, bundle):
    command = (
        [str(bundle / "native/stats_worker")]
        if language == "cpp"
        else [shutil.which("java"), "-cp", str(bundle / "java"), "StatsWorker"]
    )
    result = subprocess.run(command, input=payload, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert result.stdout == b""
    assert b"invalid request" in result.stderr
