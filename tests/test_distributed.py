import os
from pathlib import Path

import pytest
import ray

from ray_polyglot.distributed import batch_stats, compare


@pytest.fixture(scope="module")
def cluster():
    bundle = Path(os.environ.get("RAY_POLYGLOT_BUNDLE", ".build/bundle")).resolve()
    ray.init(
        address="local",
        num_cpus=2,
        include_dashboard=False,
        object_store_memory=100 * 1024 * 1024,
        runtime_env={"working_dir": str(bundle)},
    )
    yield
    ray.shutdown()


@pytest.mark.integration
def test_real_distributed_java_cpp(cluster):
    data = list(range(-512, 513))
    result = compare(data, batch_size=128, window=4)
    assert result["verified"]
    assert result["task_count"] == 18
    assert result["totals"]["java"] == result["totals"]["cpp"]
    assert os.getpid() not in result["worker_pids"]
    assert len(result["worker_pids"]) >= 2


@pytest.mark.integration
def test_empty_distributed_batch(cluster):
    assert compare([], batch_size=1)["python_baseline"] == {
        "count": 0,
        "sum": 0,
        "sum_squares": 0,
    }


@pytest.mark.integration
def test_failure_crosses_ray_boundary(cluster):
    ref = batch_stats.remote("cpp", [1000001])
    with pytest.raises(ray.exceptions.RayTaskError, match="integers"):
        ray.get(ref, timeout=30)


@pytest.mark.integration
@pytest.mark.parametrize("size", [0, 4097, True])
def test_invalid_batch_size(cluster, size):
    with pytest.raises(ValueError):
        compare([1], batch_size=size)
