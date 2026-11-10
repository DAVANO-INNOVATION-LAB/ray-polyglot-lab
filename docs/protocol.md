# RAYPOLY1 protocol

One request per process. ASCII whitespace-delimited input:

```text
RAYPOLY1 3 -4 5 6
```

The second token is the number of values (0–4096). Exactly that many integer
tokens must follow. Tokens use optional `-`, then `0` or a nonzero digit followed
by digits. Leading `+`, leading zeroes, floats, extra values, and non-ASCII input
are rejected. Supported separators are space, tab, newline, and carriage return.
The complete request cannot exceed 65,536 bytes. Each value is in
[-1,000,000, 1,000,000]. EOF terminates the request.

Success, exit 0, one JSON object on stdout:

```json
{"protocol":"RAYPOLY1","language":"cpp","count":3,"sum":7,"sum_squares":77}
```

Java uses `"language":"java"`. No other fields are accepted by the adapter.
`count`, `sum`, and `sum_squares` must be integers, not booleans or floats.
The adapter checks version, language, count and numeric bounds. The demo also
compares aggregate results with Python. Invalid requests exit 2 with a short
stderr diagnostic. The adapter does not echo input or stderr in raised errors.

The combined captured stdout/stderr limit is 65,536 bytes; exceeding it terminates
the process group. Native direct entrypoints are intended to be invoked by the
adapter, whose wall-time limit also bounds waiting for EOF.
