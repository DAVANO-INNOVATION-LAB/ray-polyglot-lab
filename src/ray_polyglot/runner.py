"""Run trusted binaries without a shell, with bounded I/O and wall time.

This is resource hygiene, not a security sandbox for untrusted executables.
POSIX process groups support timeout cleanup, but a SIGKILL of this Python
process can still orphan a detached child. See docs/architecture.md.
"""

import math
import os
import selectors
import shutil
import signal
import subprocess
import time
from pathlib import Path

from ray_polyglot.protocol import MAX_BYTES, decode, encode


class WorkerError(RuntimeError):
    """The external worker did not complete its protocol successfully."""


def run_process(
    command: list[str], payload: bytes, *, timeout_s: float = 10.0, max_bytes: int = MAX_BYTES
) -> bytes:
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be positive and finite")
    if type(max_bytes) is not int or max_bytes <= 0 or len(payload) > MAX_BYTES:
        raise ValueError("invalid I/O limit or oversized request")
    output = bytearray()
    errors = bytearray()
    deadline = time.monotonic() + timeout_s
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        shell=False,
    )
    assert process.stdin and process.stdout and process.stderr
    try:
        with selectors.DefaultSelector() as selector:
            for stream, event in (
                (process.stdin, selectors.EVENT_WRITE),
                (process.stdout, selectors.EVENT_READ),
                (process.stderr, selectors.EVENT_READ),
            ):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, event)
            offset = 0
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WorkerError(f"worker exceeded {timeout_s:g}s timeout")
                for key, _ in selector.select(min(remaining, 0.1)):
                    stream = key.fileobj
                    if stream is process.stdin:
                        try:
                            offset += os.write(stream.fileno(), payload[offset : offset + 4096])
                        except BrokenPipeError:
                            offset = len(payload)
                        if offset == len(payload):
                            selector.unregister(stream)
                            stream.close()
                        continue
                    chunk = os.read(stream.fileno(), 4096)
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    (output if stream is process.stdout else errors).extend(chunk)
                    if len(output) + len(errors) > max_bytes:
                        raise WorkerError("worker exceeded output limit")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WorkerError(f"worker exceeded {timeout_s:g}s timeout")
            try:
                code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise WorkerError(f"worker exceeded {timeout_s:g}s timeout") from exc
            if code:
                # Do not echo arbitrary inputs or child stderr into logs.
                raise WorkerError(f"worker exited with status {code}")
            return bytes(output)
    finally:
        # Also remove descendants left by a successfully exited trusted worker.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


def run_native(language: str, values: list[int], *, bundle: Path, timeout_s: float = 10.0) -> dict:
    payload = encode(values)
    if language == "cpp":
        command = [str(bundle.resolve() / "native" / "stats_worker")]
    elif language == "java":
        java = shutil.which("java")
        if not java:
            raise WorkerError("java is not installed on this worker")
        command = [java, "-Xmx64m", "-cp", str(bundle.resolve() / "java"), "StatsWorker"]
    else:
        raise ValueError("language must be java or cpp")
    try:
        return decode(run_process(command, payload, timeout_s=timeout_s), language, len(values))
    except (OSError, ValueError) as exc:
        raise WorkerError(f"{language} worker failed: {type(exc).__name__}") from exc
