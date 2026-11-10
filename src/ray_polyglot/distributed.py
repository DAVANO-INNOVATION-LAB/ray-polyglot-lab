"""Ray tasks orchestrating Java/C++ processes through public Python APIs."""

import os
from pathlib import Path

import ray

from ray_polyglot.protocol import expected
from ray_polyglot.runner import run_native


@ray.remote(num_cpus=1, max_retries=0)
def batch_stats(language: str, values: list[int], timeout_s: float = 10.0) -> dict:
    result = run_native(language, values, bundle=Path.cwd(), timeout_s=timeout_s)
    return {
        **result,
        "worker_pid": os.getpid(),
        "node_id": ray.get_runtime_context().get_node_id(),
    }


def compare(values: list[int], batch_size: int = 256, window: int = 8) -> dict:
    if type(batch_size) is not int or not 1 <= batch_size <= 4096:
        raise ValueError("batch_size must be an integer in [1, 4096]")
    if type(window) is not int or not 1 <= window <= 128:
        raise ValueError("window must be an integer in [1, 128]")
    if not ray.is_initialized():
        raise RuntimeError("initialize Ray with the staged worker bundle first")
    # Bound pending tasks. Input itself remains in driver memory for this demo.
    totals = {lang: {"count": 0, "sum": 0, "sum_squares": 0} for lang in ("java", "cpp")}
    baseline = {"count": 0, "sum": 0, "sum_squares": 0}
    task_count = 0
    worker_pids = set()
    node_ids = set()
    pending = []

    def collect() -> None:
        nonlocal task_count
        ready, rest = ray.wait(pending, num_returns=1, timeout=60)
        if not ready:
            raise TimeoutError("Ray task did not complete within 60 seconds")
        pending[:] = rest
        result = ray.get(ready[0])
        task_count += 1
        worker_pids.add(result["worker_pid"])
        node_ids.add(result["node_id"])
        for key in baseline:
            totals[result["language"]][key] += result[key]

    try:
        for offset in range(0, max(len(values), 1), batch_size):
            batch = values[offset : offset + batch_size]
            reference = expected(batch)
            for key in baseline:
                baseline[key] += reference[key]
            for language in totals:
                pending.append(batch_stats.remote(language, batch))
                if len(pending) >= window:
                    collect()
        while pending:
            collect()
    except BaseException:
        for ref in pending:
            ray.cancel(ref, force=False)
        raise
    if any(total != baseline for total in totals.values()):
        raise AssertionError("Java/C++ results differ from the exact Python baseline")
    return {
        "verified": True,
        "ray_version": ray.__version__,
        "totals": totals,
        "python_baseline": baseline,
        "task_count": task_count,
        "worker_pids": sorted(worker_pids),
        "node_ids": sorted(node_ids),
    }
