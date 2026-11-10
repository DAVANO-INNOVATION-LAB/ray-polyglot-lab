"""Compile and stage only deployable code, not the repo or credentials."""

import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / ".build" / "bundle"


def compile_bundle(destination: Path) -> None:
    """Build only current inputs into a new, empty directory."""
    (destination / "native").mkdir()
    (destination / "java").mkdir()
    compiler = shutil.which("g++")
    java = shutil.which("java")
    if not compiler or not java:
        raise SystemExit("Install a C++17 compiler and a JDK (17+) first.")
    javac = shutil.which("javac")
    java_command = [javac] if javac else [java, "com.sun.tools.javac.Main"]
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            str(ROOT / "workers/cpp/stats_worker.cpp"),
            "-o",
            str(destination / "native/stats_worker"),
        ],
        check=True,
    )
    subprocess.run(
        [
            *java_command,
            "--release",
            "17",
            "-Xlint:all",
            "-Werror",
            "-d",
            str(destination / "java"),
            str(ROOT / "workers/java/StatsWorker.java"),
        ],
        check=True,
    )
    shutil.copytree(
        ROOT / "src/ray_polyglot",
        destination / "ray_polyglot",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (destination / "manifest.json").write_text(
        json.dumps(
            {
                "ray": "2.60.0",
                "java_target": "17",
                "system": platform.system(),
                "machine": platform.machine(),
                "libc": platform.libc_ver(),
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    """Publish a clean build only after all steps succeed.

    Do not run concurrent builds or submit the bundle while replacing it.
    The two directory renames have a brief gap; this is not a deployment service.
    """
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".bundle-", dir=BUNDLE.parent) as directory:
        temporary = Path(directory)
        staged = temporary / "staged"
        staged.mkdir()
        compile_bundle(staged)
        previous = temporary / "previous"
        if BUNDLE.exists():
            BUNDLE.rename(previous)
        try:
            staged.rename(BUNDLE)
        except BaseException:
            if previous.exists():
                previous.rename(BUNDLE)
            raise
    print(f"Built worker bundle: {BUNDLE}")


if __name__ == "__main__":
    main()
