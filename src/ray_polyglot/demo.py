"""Start a local runtime or connect to an explicitly selected trusted cluster."""

import argparse
import json
import random
from pathlib import Path

import ray

from ray_polyglot.distributed import compare


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=Path(".build/bundle"))
    parser.add_argument("--address", help="Trusted Ray cluster address; omitted starts local Ray")
    parser.add_argument("--items", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--cpus", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not 0 <= args.items <= 1_000_000 or args.cpus < 1:
        parser.error("items must be 0..1000000 and cpus must be positive")
    bundle = args.bundle.resolve()
    if not (bundle / "manifest.json").is_file():
        parser.error("missing compiled bundle; run python scripts/build.py first")
    kwargs = (
        {"address": args.address}
        if args.address
        else {
            "address": "local",
            "num_cpus": args.cpus,
            "include_dashboard": False,
            "object_store_memory": 100 * 1024 * 1024,
        }
    )
    # Explicit staging prevents .gitignore from accidentally dropping compiled workers.
    ray.init(**kwargs, runtime_env={"working_dir": str(bundle)})
    try:
        rng = random.Random(args.seed)
        data = [rng.randint(-1_000_000, 1_000_000) for _ in range(args.items)]
        print(json.dumps(compare(data, args.batch_size), indent=2))
    finally:
        ray.shutdown()


if __name__ == "__main__":
    main()
