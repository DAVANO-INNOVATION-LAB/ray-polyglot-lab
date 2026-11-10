# Architecture, trust, and operating limits

## Packaging

`scripts/build.py` compiles original source, targets Java 17 and C++17, and stages
a self-contained *application* directory under `.build/bundle`. Ray 2.60.0 is
pinned. Java and standard native runtime libraries are external prerequisites.
The build manifest records architecture and libc information; it documents the
build, but it is not a runtime compatibility attestation or a signature.
Every build uses a fresh staging directory, replacing the previous bundle only
after compilation and staging succeed. Rebuilds do not retain stale files.
Do not build concurrently or submit a bundle while it is being replaced.

Ray's public `ray.remote`, `ray.wait`, `ray.get`, `ray.cancel`, and
`runtime_env.working_dir` APIs implement scheduling and artifact transfer. Keep Ray services inside a
trusted network and retain authentication. Local startup is not a firewall or
network isolation guarantee.

## Scheduling and failures

Each task requests one logical CPU and sets `max_retries=0`. Logical CPUs are
scheduler accounting, not cgroup limits. `compare` caps pending tasks (8 by
default, configurable 1–128) and uses a 60-second wait deadline between completed
tasks. A subprocess has a separate 10-second wall-time deadline. A JVM is bounded
to `-Xmx64m` heap; that is not its full resident-memory usage.

Failed tasks propagate as Ray exceptions. The driver requests cooperative
cancellation of other pending tasks; it does not claim immediate cancellation of
native code. In normal adapter exceptions, timeout, and completion, a finally
block terminates the spawned POSIX process group and reaps the direct child.

## Worker-crash limitation

`start_new_session=True` gives the adapter a process group it can terminate,
including ordinary descendants that remain in that group. It also detaches the
subprocess from Ray's own process-group cleanup. If the Python Ray worker is
SIGKILLed, its `finally` block cannot run, so descendants can survive. Processes
that detach themselves again can also escape this cleanup. Use per-job containers
or cgroups and explicit lifecycle supervision before production deployment.
This prototype has no worker-death/orphan-free guarantee.

## Trust boundary

This project runs only fixed, trusted, locally built programs. Passing arbitrary
commands, JARs, scripts, or binaries from untrusted users is outside scope. The
adapter is not a security sandbox. Subprocesses inherit the worker environment;
do not put unnecessary credentials in it. Neither the bundle nor test reports
should contain credentials, auth files, private user data, or copied environment
variables. Ray cluster credentials stay outside the staged bundle.

There is no live deployment, production connection, privileged operation,
credential upload, arbitrary-code API, or upstream mutation in the demo.

## Deliberate next steps

1. Add multi-node CI in an isolated container image, including binary/ABI checks.
2. Add supervised persistent Java/C++ processes for large batches, then benchmark.
3. Add idempotency keys and explicit retry contracts before enabling retries.
4. Evaluate native Ray Java/C++ APIs separately, including matching artifact builds.

Sources: [Ray dependency handling](https://docs.ray.io/en/latest/ray-core/handling-dependencies.html),
[user-spawned process lifecycle](https://docs.ray.io/en/latest/ray-core/user-spawn-processes.html),
[security](https://docs.ray.io/en/latest/ray-security/index.html).
