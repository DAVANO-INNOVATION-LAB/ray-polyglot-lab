# SPDX-License-Identifier: Apache-2.0
"""Review-only tests of code extracted verbatim from the proposed guide."""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "candidate/doc/source/core/examples/polyglot-batch.md"


@pytest.fixture(scope="session")
def example(tmp_path_factory):
    root = tmp_path_factory.mktemp("polyglot-guide")
    blocks = re.findall(r"^```(\w+)\n(.*?)^```$", GUIDE.read_text(), re.M | re.S)
    for language, filename in (
        ("cpp", "stats_worker.cpp"),
        ("java", "StatsWorker.java"),
        ("python", "polyglot_driver.py"),
    ):
        matches = [content for tag, content in blocks if tag == language]
        assert len(matches) == 1
        (root / filename).write_text(matches[0])
    build = next(
        content for tag, content in blocks if tag == "bash" and "mktemp" in content
    )
    built = subprocess.run(
        ["bash", "-c", build], cwd=root, capture_output=True, text=True, check=True
    )
    bundle = Path(built.stdout.strip())
    spec = importlib.util.spec_from_file_location(
        "polyglot_driver", root / "polyglot_driver.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, bundle, root


@pytest.mark.parametrize("language", ["java", "cpp"])
@pytest.mark.parametrize(
    "values", [[], [0], [-1, 2, -3], [1000000] * 4096, [-1000000] * 4096]
)
def test_native_parity(example, language, values):
    module, bundle, _ = example
    assert module.run_worker(language, values, bundle) == module.expected(values)


@pytest.mark.parametrize(
    "values", [[True], [1.0], [None], [1000001], [-1000001], [0] * 4097]
)
def test_invalid_input(example, values):
    module, bundle, _ = example
    with pytest.raises(ValueError):
        module.run_worker("cpp", values, bundle)


@pytest.mark.parametrize("language", ["java", "cpp"])
@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"RAYPOLY1 -1",
        b"RAYPOLY1 4097",
        b"RAYPOLY1 1",
        b"RAYPOLY1 0 1",
        b"RAYPOLY1 1 1.5",
        b"RAYPOLY1 1 1000001",
        b"RAYPOLY1 1 -1000001",
        b"RAYPOLY1 1 +1",
        b"RAYPOLY1 1 01",
        b"RAYPOLY1 1 \xff",
        b"x" * 65537,
    ],
)
def test_malformed_native_input(example, language, payload):
    _, bundle, _ = example
    command = (
        [str(bundle / "native/stats_worker")]
        if language == "cpp"
        else [shutil.which("java"), "-cp", str(bundle / "java"), "StatsWorker"]
    )
    result = subprocess.run(command, input=payload, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert result.stdout == b""
    assert b"invalid request" in result.stderr


def test_direct_cli(example):
    _, bundle, root = example
    result = subprocess.run(
        [
            sys.executable,
            str(root / "polyglot_driver.py"),
            "--bundle",
            str(bundle),
            "--direct",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    response = json.loads(result.stdout)
    assert (
        response["java"]
        == response["cpp"]
        == {"count": 4096, "sum": -2048, "sum_squares": 5726623744}
    )


def test_relocated_bundle(example, tmp_path):
    module, bundle, _ = example
    relocated = tmp_path / "copied"
    shutil.copytree(bundle, relocated)
    assert {p.name for p in relocated.iterdir()} == {
        "native",
        "java",
        "polyglot_driver.py",
    }
    for language in ("java", "cpp"):
        assert module.run_worker(language, [-3, 2, 7], relocated) == module.expected(
            [-3, 2, 7]
        )


def fake_worker(tmp_path, code):
    native = tmp_path / "native"
    native.mkdir()
    script = native / "stats_worker"
    script.write_text(f"#!{sys.executable}\n" + code)
    script.chmod(0o700)
    return tmp_path


def test_timeout_reaps_direct_child(example, tmp_path):
    module, _, _ = example
    pid_file = tmp_path / "pid"
    bundle = fake_worker(
        tmp_path,
        f"import os,time\nopen({str(pid_file)!r},'w').write(str(os.getpid()))\ntime.sleep(30)\n",
    )
    with pytest.raises(RuntimeError, match="timed out"):
        module.run_worker("cpp", [1], bundle, timeout_s=0.5)
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_error_redaction(example, tmp_path):
    module, _, _ = example
    bundle = fake_worker(
        tmp_path, "import sys\nprint('private-value',file=sys.stderr)\nsys.exit(7)\n"
    )
    with pytest.raises(RuntimeError, match="status 7") as error:
        module.run_worker("cpp", [1], bundle)
    assert "private-value" not in str(error.value)


@pytest.mark.parametrize(
    "reply",
    [
        "[]",
        "{}",
        '{"protocol":"RAYPOLY1","language":"cpp","count":true,"sum":1,"sum_squares":1}',
        '{"protocol":"RAYPOLY1","language":"cpp","count":1,"sum":2,"sum_squares":1}',
        "x" * 1025,
    ],
)
def test_bad_worker_reply(example, tmp_path, reply):
    module, _, _ = example
    bundle = fake_worker(tmp_path, f"print({reply!r})\n")
    with pytest.raises(RuntimeError):
        module.run_worker("cpp", [1], bundle)


@pytest.mark.parametrize(
    "kwargs", [{"batch_size": 0}, {"batch_size": True}, {"window": 0}, {"window": 129}]
)
def test_invalid_scheduling_options(example, kwargs):
    module, _, _ = example
    with pytest.raises(ValueError):
        module.compare([1], **kwargs)


@pytest.mark.integration
@pytest.mark.parametrize("values", [[], [-5, 2, 9], list(range(-2048, 2048))])
def test_real_ray(example, values):
    module, bundle, _ = example
    module.ray.init(
        address="local",
        num_cpus=2,
        include_dashboard=False,
        runtime_env={"working_dir": str(bundle)},
    )
    try:
        result = module.compare(values)
        baseline = {
            "count": len(values),
            "sum": sum(values),
            "sum_squares": sum(x * x for x in values),
        }
        assert result["totals"] == {"java": baseline, "cpp": baseline}
        assert result["verified"]
        assert result["task_count"] == 2 * max(1, (len(values) + 255) // 256)
    finally:
        module.ray.shutdown()


@pytest.mark.parametrize("reply", [b"private-invalid-json", b"\xffprivate-output"])
def test_invalid_json_redaction(example, tmp_path, reply):
    module, _, _ = example
    bundle = fake_worker(tmp_path, f"import sys\nsys.stdout.buffer.write({reply!r})\n")
    with pytest.raises(RuntimeError, match="Invalid worker JSON") as error:
        module.run_worker("cpp", [1], bundle)
    assert "private" not in str(error.value)


def test_java_json_is_locale_independent(example):
    _, bundle, _ = example
    result = subprocess.run(
        [
            shutil.which("java"),
            "-Duser.language=ar",
            "-Duser.country=EG",
            "-cp",
            str(bundle / "java"),
            "StatsWorker",
        ],
        input=b"RAYPOLY1 3 -1 2 3",
        capture_output=True,
        check=True,
        timeout=10,
    )
    assert json.loads(result.stdout)["sum"] == 4
    assert result.stdout.isascii()
