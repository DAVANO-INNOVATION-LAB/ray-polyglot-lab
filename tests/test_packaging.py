"""Exercise pinned Ray's real packager without a running cluster.

These test-only private APIs are intentionally version-specific; application
execution uses public runtime_env configuration.
"""

import zipfile

from ray._private.runtime_env.packaging import create_package, unzip_package

from ray_polyglot.runner import run_native


def test_ray_bundle_roundtrip(bundle, tmp_path):
    archive = tmp_path / "bundle.zip"
    create_package(str(bundle), archive, include_gitignore=True)
    with zipfile.ZipFile(archive) as zipped:
        names = set(zipped.namelist())
        assert "native/stats_worker" in names
        assert "java/StatsWorker.class" in names
        assert "ray_polyglot/runner.py" in names
        assert not any("auth_token" in name or ".git/" in name for name in names)
    relocated = tmp_path / "worker-copy"
    unzip_package(str(archive), str(relocated), False, False)
    for language in ("java", "cpp"):
        result = run_native(language, [-4, 5, 6], bundle=relocated)
        assert result["sum"] == 7
        assert result["sum_squares"] == 77
