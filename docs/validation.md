# Validation record

Date: 2026-11-10. This document distinguishes executed tests from intended behavior.

## Local checks executed successfully

- Python 3.12.14, Ray 2.60.0, pytest 8.3.5, Ruff 0.12.2.
- GCC 14.2.0 compiled the C++ worker with C++17, warnings-as-errors and pedantic checks.
- OpenJDK 21.0.13 compiler compiled the Java worker with `--release 17`, all lint,
  and warnings-as-errors; the worker ran on Java 21.0.13.
- `pytest -q -m 'not integration'`: **77 passed**, 6 integration tests deselected.
- `ruff check .`, `ruff format --check .`, and `git diff --check`: passed.
- Editable Python package installation succeeded.
- Ray's actual package/unpackage round trip preserved both worker artifacts and
  native execute permissions; relocated Java/C++ workers returned correct results.
- Clean-build regressions verify stale files are removed, either compiler failure
  preserves the prior bundle, and a publication failure restores it.

Coverage includes actual Java/C++ execution; empty, negative, boundary and seeded
random inputs; malformed requests and protocol replies; exact integer agreement;
unknown languages; missing binaries; stdout/stderr floods; process timeout; and
redaction of worker stderr from raised exceptions.

The build machine had a stripped JRE without compiler metadata. The matching
official Debian OpenJDK package was extracted into an ignored local build directory
to supply the compiler metadata. This workaround is not shipped or required for
normal JDK installations. No compiler binary or third-party source is committed.

## Local full-Ray tests blocked by environment

Six tests are marked `integration`: real distributed Java/C++ tasks, empty-batch
execution, error propagation through Ray, and three invalid-batch cases. They
attempted to start an actual Ray runtime but **did not reach workload execution**
in this restricted workspace.

Ray's GCS started. The `raylet` then aborted when the Plasma object store attempted
to open its required Unix socket with `Operation not permitted`. An approved
escalated run retained the same restriction. No authentication was disabled and
the restriction was not bypassed. A local-only Ray setting was tried to avoid the
container's unreachable advertised hostname; it did not resolve the socket limit.

Thus 77 passing tests do **not** establish an end-to-end distributed Ray pass.
No fake Ray replacement or `local_mode` was used to claim a pass.

## Hosted full-Ray validation passed

The committed GitHub Actions workflow compiles on Ubuntu 24.04 with Java 17 and
Python 3.12, runs the entire test suite including real Ray, and runs a 4096-item
demo. [Run 42918940891](https://github.com/DAVANO-INNOVATION-LAB/ray-polyglot-lab/actions/runs/42918940891)
completed successfully for implementation commit
`88b905b10107201c2f9416fa174e977330448048`:

- **83 tests passed** in 9.19 seconds, including all six full-Ray integration tests.
- Java 17.0.21+9 and Python 3.12.16 on Ubuntu 24.04.5.
- The demo executed **32 real Ray tasks** on two worker processes on one node.
- Each language processed 4096 integers: sum `31464857`, sum of squares
  `1330024606232077`, matching the independent Python baseline exactly.
- Runtime artifact transfer succeeded; Ray token authentication remained enabled.
- Compile, lint, formatting, full tests, and the CLI demo all passed.

This resolves the end-to-end validation gap on a normal Linux runner. The local
workspace socket restriction described above still applies. It is not a test
of multiple machines, a performance benchmark, or validation of native Ray APIs.

## Remaining validation

Not yet validated: multi-node deployment, throughput/speedup, native Ray Java/C++
API behavior, worker-death orphan handling, heterogeneous ABIs, production
security, and retry semantics. Read the limitations before extending this demo.
