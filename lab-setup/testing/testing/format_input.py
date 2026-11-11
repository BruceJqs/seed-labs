"""Interpret ordinary input traces from the supplied lab programs."""
import re


def buffer_trace(logs, byte_count):
    # The caller supplies logs for one sequential request. Starting stack is
    # written to stderr; Docker may timestamp it after the stdout result.
    # Correlate only the byte count and completion on the same stdout stream.
    received = list(re.finditer(r"Input size: (\d+)", logs))
    completed = list(re.finditer(r"==== Returned Properly ====", logs))
    if not received or not completed:
        return None
    if len(received) != 1 or len(completed) != 1:
        raise ValueError("multiple stack traces in one request's log window")
    if completed[0].start() < received[0].end():
        raise ValueError("stack completion precedes its input byte count")
    actual = int(received[0][1])
    if actual != byte_count:
        raise ValueError(f"normal stack received {actual} bytes, expected {byte_count}")
    return {"received_bytes": actual, "returned_properly": True}


def normal_trace(logs, marker, byte_count):
    """Return None for incomplete logs; reject completed but incorrect traces."""
    # The server prints addresses to its console, not to the TCP client.
    position = logs.find(marker)
    if position < 0:
        return None
    start = logs.rfind("Starting format", 0, position)
    if start < 0:
        return None
    end = logs.find("Starting format", position)
    block = logs[start:end] if end >= 0 else logs[start:]
    if "Returned properly" not in block:
        return None
    before = re.search(r"The target variable's value \(before\):\s*(0x[0-9a-fA-F]+)", block)
    after = re.search(r"The target variable's value \(after\):\s*(0x[0-9a-fA-F]+)", block)
    received = re.search(r"Received (\d+) bytes\.", block)
    if not before or not after or not received:
        raise ValueError("normal-input trace is missing byte count or target values")
    if int(received[1]) != byte_count:
        raise ValueError(f"received {received[1]} bytes, expected {byte_count}")
    if int(before[1], 16) != int(after[1], 16):
        raise ValueError(f"normal input changed target: {before[1]} -> {after[1]}")
    return {"received_bytes": int(received[1]), "target_before": before[1], "target_after": after[1],
            "returned_properly": True}
