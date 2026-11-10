"""Versioned, integer-only protocol shared by independently compiled workers."""

import json

PROTOCOL = "RAYPOLY1"
MAX_ITEMS = 4096
MAX_VALUE = 1_000_000
MAX_BYTES = 65_536


def encode(values: list[int]) -> bytes:
    if not isinstance(values, list) or len(values) > MAX_ITEMS:
        raise ValueError(f"values must be a list with at most {MAX_ITEMS} items")
    if any(type(value) is not int or abs(value) > MAX_VALUE for value in values):
        raise ValueError(f"values must be integers in [-{MAX_VALUE}, {MAX_VALUE}]")
    return f"{PROTOCOL} {len(values)} {' '.join(map(str, values))}\n".encode("ascii")


def expected(values: list[int]) -> dict[str, int]:
    encode(values)
    return {"count": len(values), "sum": sum(values), "sum_squares": sum(v * v for v in values)}


def decode(output: bytes, language: str, count: int) -> dict:
    if len(output) > MAX_BYTES:
        raise ValueError("worker response exceeds protocol limit")
    result = json.loads(output)
    if not isinstance(result, dict) or set(result) != {
        "protocol",
        "language",
        "count",
        "sum",
        "sum_squares",
    }:
        raise ValueError("worker returned an invalid response shape")
    if result["protocol"] != PROTOCOL or result["language"] != language:
        raise ValueError("worker returned a mismatched protocol or language")
    if any(type(result[k]) is not int for k in ("count", "sum", "sum_squares")):
        raise ValueError("worker returned a non-integer statistic")
    if result["count"] != count:
        raise ValueError("worker returned a mismatched count")
    if abs(result["sum"]) > count * MAX_VALUE or not (
        0 <= result["sum_squares"] <= count * MAX_VALUE**2
    ):
        raise ValueError("worker returned an out-of-range statistic")
    return result
