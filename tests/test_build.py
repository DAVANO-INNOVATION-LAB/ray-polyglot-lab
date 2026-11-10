import importlib.util
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def builder(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/build.py"
    spec = importlib.util.spec_from_file_location("polyglot_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "BUNDLE", tmp_path / "bundle")
    return module


def populate_existing(bundle):
    (bundle / "ray_polyglot").mkdir(parents=True)
    (bundle / "ray_polyglot/obsolete.py").write_text("old code")
    (bundle / "unknown-marker").write_text("must not be packaged")
    (bundle / "java").mkdir()
    (bundle / "java/OldWorker.class").write_bytes(b"old class")
    (bundle / "manifest.json").write_text("old manifest")


def snapshot(directory):
    return {
        str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }


def fake_compile(command, *, check):
    assert check is True
    if "-o" in command:
        Path(command[command.index("-o") + 1]).write_bytes(b"new executable")
    else:
        (Path(command[command.index("-d") + 1]) / "StatsWorker.class").write_bytes(b"new class")


def test_clean_rebuild_drops_stale_files(builder, monkeypatch):
    populate_existing(builder.BUNDLE)
    monkeypatch.setattr(builder.shutil, "which", lambda name: f"/test/{name}")
    monkeypatch.setattr(builder.subprocess, "run", fake_compile)
    builder.main()
    files = snapshot(builder.BUNDLE)
    assert "unknown-marker" not in files
    assert "ray_polyglot/obsolete.py" not in files
    assert "java/OldWorker.class" not in files
    assert files["native/stats_worker"] == b"new executable"
    assert files["java/StatsWorker.class"] == b"new class"
    assert "ray_polyglot/runner.py" in files
    assert not list(builder.BUNDLE.parent.glob(".bundle-*"))


@pytest.mark.parametrize("fail_step", [1, 2])
def test_compile_failure_preserves_old_bundle(builder, monkeypatch, fail_step):
    populate_existing(builder.BUNDLE)
    before = snapshot(builder.BUNDLE)
    monkeypatch.setattr(builder.shutil, "which", lambda name: f"/test/{name}")
    calls = 0

    def fail(command, *, check):
        nonlocal calls
        calls += 1
        if calls == fail_step:
            raise subprocess.CalledProcessError(1, command)
        fake_compile(command, check=check)

    monkeypatch.setattr(builder.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        builder.main()
    assert snapshot(builder.BUNDLE) == before
    assert not list(builder.BUNDLE.parent.glob(".bundle-*"))


def test_publish_failure_restores_previous_bundle(builder, monkeypatch):
    populate_existing(builder.BUNDLE)
    before = snapshot(builder.BUNDLE)
    monkeypatch.setattr(builder.shutil, "which", lambda name: f"/test/{name}")
    monkeypatch.setattr(builder.subprocess, "run", fake_compile)
    rename = Path.rename

    def fail_staging(path, destination):
        if path.name == "staged":
            raise OSError("simulated publication failure")
        return rename(path, destination)

    monkeypatch.setattr(Path, "rename", fail_staging)
    with pytest.raises(OSError, match="publication"):
        builder.main()
    assert snapshot(builder.BUNDLE) == before
