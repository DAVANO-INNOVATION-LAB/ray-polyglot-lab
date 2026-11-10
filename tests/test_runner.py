import sys
import time

import pytest

from ray_polyglot.runner import WorkerError, run_native, run_process


def command(code):
    return [sys.executable, "-c", code]


def test_stdin_roundtrip():
    data = b"x" * 65536
    assert (
        run_process(command("import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"), data)
        == data
    )


def test_nonzero_exit_redacts_stderr():
    with pytest.raises(WorkerError, match="status 7") as exc:
        run_process(command("import sys; print('private', file=sys.stderr); sys.exit(7)"), b"")
    assert "private" not in str(exc.value)


def test_timeout():
    start = time.monotonic()
    with pytest.raises(WorkerError, match="timeout"):
        run_process(command("import time; time.sleep(30)"), b"", timeout_s=0.2)
    assert time.monotonic() - start < 5


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_output_flood(stream):
    with pytest.raises(WorkerError, match="output limit"):
        run_process(command(f"import sys; sys.{stream}.write('x' * 100000)"), b"", max_bytes=1024)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        run_process(command("pass"), b"", timeout_s=timeout)


def test_closed_output_still_respects_timeout():
    with pytest.raises(WorkerError, match="timeout"):
        run_process(
            command("import os,time; os.close(1); os.close(2); time.sleep(30)"), b"", timeout_s=0.2
        )


def test_missing_artifact(tmp_path):
    with pytest.raises(WorkerError, match="FileNotFoundError"):
        run_native("cpp", [1], bundle=tmp_path)


def test_unknown_language(tmp_path):
    with pytest.raises(ValueError):
        run_native("java; echo nope", [1], bundle=tmp_path)
