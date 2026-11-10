# Ray integration and upstream contribution research

Checked 2026-11-10. This repository is independent original code, not a Ray fork.

## Why start with an adapter

[Ray 2.60.0](https://github.com/ray-project/ray/releases/tag/ray-2.60.0) was released
on 2026-11-04 and was the latest published release checked for this experiment.
[Ray's installation guide](https://docs.ray.io/en/latest/ray-overview/installation.html)
labels the native Java and C++ APIs experimental/community-supported. Native
[cross-language calls](https://docs.ray.io/en/latest/ray-core/cross-language.html)
also impose packaging and type compatibility constraints.

The [Java publishing issue #55201](https://github.com/ray-project/ray/issues/55201)
remained open at research time; a maintainer reported paused JAR publishing in
2025. Therefore do not assume that a Maven artifact matching the newest Python
Ray release exists. This adapter uses current Ray Python APIs and ordinary Java/
C++ programs without claiming native cross-language API coverage.

## Concrete possible C++ contribution

[Issue #51205](https://github.com/ray-project/ray/issues/51205) requests C++ actor
`max_task_retries` support. Current source inspection found:

- `cpp/include/ray/api/actor_creator.h` has no `SetMaxTaskRetries` builder method.
- `cpp/include/ray/api/task_options.h` has no `max_task_retries` field on
  `ActorCreationOptions`.
- `cpp/src/ray/runtime/task/native_task_submitter.cc` hardcodes actor creation's
  `max_task_retries` argument to 0.

The issue was open, unassigned, and community-backlog, with maintainer encouragement.
Issue-number and method-name searches found no direct duplicate PR in this check,
but this is not proof none exists. Recheck against the current tree before work;
related retry changes include #66818 and #67503.

A narrowly scoped contribution could expose the actor retry option, thread it
through submission, and add real worker/actor failure recovery tests. It needs a
native Ray build and cluster tests, which this adapter does **not** supply. No
patch claiming that bug is fixed is included here.

## AI-assisted contribution policy

[Ray's AGENTS.md](https://github.com/ray-project/ray/blob/master/AGENTS.md) permits
AI assistance but rejects pure code-agent PRs. It requires the human contributor
to review every changed line, understand and be able to defend it, run tests, and
disclose AI use. It also asks for concrete test results and duplicate-work checks.

Accordingly, no upstream issue comment, fork, or PR was created automatically.
Before an upstream PR: agree on scope, obtain human review and independently run
the required tests, check for duplicate work, and disclose assistance. A fork
becomes useful at that point; it is unnecessary to validate this external adapter.
