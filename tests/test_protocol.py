import json

import pytest

from ray_polyglot.protocol import decode, encode, expected


@pytest.mark.parametrize("values", [[True], [1.1], [None], [1000001], [-1000001], [0] * 4097])
def test_reject_invalid_values(values):
    with pytest.raises(ValueError):
        encode(values)


def test_exact_bounds():
    values = [-1000000, 1000000] * 2048
    assert expected(values) == {"count": 4096, "sum": 0, "sum_squares": 4096000000000000}
    assert len(encode(values)) < 65536


@pytest.mark.parametrize(
    "change",
    [
        {"count": True},
        {"sum": 1.0},
        {"sum_squares": -1},
        {"language": "python"},
        {"protocol": "v2"},
        {"count": 2},
        {"extra": 1},
        {"sum": 1000001},
    ],
)
def test_bad_response(change):
    result = {"protocol": "RAYPOLY1", "language": "java", "count": 1, "sum": 1, "sum_squares": 1}
    result.update(change)
    with pytest.raises(ValueError):
        decode(json.dumps(result).encode(), "java", 1)


@pytest.mark.parametrize("data", [b"[]", b"garbage", b"{}", b"x" * 65537])
def test_bad_json(data):
    with pytest.raises(ValueError):
        decode(data, "java", 1)
