# Ray Polyglot Lab

A small, real integration between **Ray 2.60.0**, compiled **Java**, and **C++17**
batch workloads. Ray schedules Python tasks; each task executes a trusted Java
or C++ program through a bounded, versioned stdin/stdout protocol. Both languages
compute exact integer statistics and are checked against an independent Python
baseline.

This is a **subprocess adapter**, not Ray's native Java/C++ cross-language API.
It needs no Ray fork, JNI integration, Maven dependency, or C++ Ray SDK build.
Native Ray APIs are a separate possible follow-on.

**Verified:** [hosted CI](https://github.com/DAVANO-INNOVATION-LAB/ray-polyglot-lab/actions/runs/42918940891)
passed all 83 tests, including real Ray execution. The 4096-item demo completed
32 tasks on two worker processes with matching Java, C++, and Python results.

## Run it

Requirements: Linux, Python 3.11 or 3.12, a JDK 17+, and a C++17 compiler (`g++`).
Use a normal full JDK, not a stripped JRE missing compiler platform metadata.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/build.py
pytest -q
ruff check .
ruff format --check .
ray-polyglot --items 4096 --batch-size 256 --cpus 2
```

The default demo starts a new local Ray runtime with two CPU scheduling slots.
It submits 32 tasks: 16 Java batches and 16 C++ batches. The JSON report contains
the verified totals, task count, Ray worker process IDs, and node IDs. Distinct
worker processes on **one node** demonstrate scheduling and serialization, not
multi-machine deployment or speedup.

Ray 2.60 enables local token authentication by default. Keep it enabled. If your
home directory is read-only, give this test a private writable HOME, rather than
disabling authentication:

```sh
mkdir -p .build/test-home
(umask 077; HOME="$PWD/.build/test-home" pytest -q)
```

No cloud account or existing production Ray cluster is required. CI is included
in `.github/workflows/test.yml`; see [validation](docs/validation.md) for actual
observed results and remaining limits.

## What it demonstrates

- Real Java and C++ processes, not mocks or Python reimplementations.
- Correct results for negative numbers, empty batches, and integer boundary values.
- Staged runtime artifacts distributed using Ray's `runtime_env.working_dir`.
- CPU scheduling declarations, bounded in-flight tasks, explicit task failure.
- Protocol validation, request/output limits, subprocess timeouts, and cleanup.
- No shell command construction from input; only fixed trusted worker commands.
- Automatic Ray retries disabled for these tasks, so non-idempotent workloads
  are not silently retried by this adapter.

## Architecture and limitations

`driver → Ray Python task → Java/C++ subprocess → JSON result → checked aggregate`

Workers calculate count, sum, and sum-of-squares for up to 4096 signed integers
per request. Values are restricted to ±1,000,000, keeping per-batch results within
signed 64-bit range. Python aggregates retain arbitrary-precision integers.

Launching a JVM for every batch is intentionally simple and has significant
startup cost. This is a correctness and packaging demonstration, not a throughput
benchmark or a production service. It does not provide a sandbox for hostile
executables, exactly-once execution, persistent actors, or hard CPU isolation.

See [architecture and security](docs/architecture.md),
[protocol](docs/protocol.md), and [upstream research](docs/upstream.md).

## Existing cluster (not validated here)

All nodes must have the same Ray/Python versions, Java 17+, and a native ABI
compatible with the compiled binary. Build inside the deployment image. Submit
only to a trusted cluster using its existing authentication configuration:

```sh
ray-polyglot --address '<trusted-cluster-address>' --bundle .build/bundle
```

The bundle contains only the Python adapter, Java classes, C++ executable, and a
build manifest. Compiled binaries are not committed. Ray stages the bundle on
workers; source-tree `.gitignore` rules therefore cannot silently omit binaries
from the package. The JVM and native dynamic libraries are **not** shipped.

## Project status

Original experimental code for DAVANO Innovation Lab. Not affiliated with or
endorsed by the Ray project. No upstream PR has been submitted. No open-source
license grant is asserted by this private prototype; select a license before
publishing it publicly or contributing code upstream.
