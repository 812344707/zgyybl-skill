#!/usr/bin/env python3
"""Render supplied bracket fills without rewriting surrounding clinical text.

Read {"template": str, "fills": [str | null | {"preserve": true}, ...],
"keep_brackets": bool}
from stdin; write only the result to stdout. No patient files are created.
"""

import json
import sys


def fill_brackets(template, fills, keep_brackets=True):
    if not isinstance(template, str):
        raise ValueError("template must be a string")
    if not isinstance(fills, list):
        raise ValueError("fills must be a list")
    if type(keep_brackets) is not bool:
        raise ValueError("keep_brackets must be a boolean")

    spans = []
    start = None
    for index, character in enumerate(template):
        if character == "[":
            if start is not None:
                raise ValueError("nested brackets require an explicit target")
            start = index
        elif character == "]":
            if start is None:
                raise ValueError("unmatched closing bracket")
            spans.append((start, index))
            start = None
    if start is not None:
        raise ValueError("unmatched opening bracket")
    if len(fills) != len(spans):
        raise ValueError("fill count must match bracket pair count")

    values = []
    for value in fills:
        if isinstance(value, dict) and len(value) == 1 and value.get("preserve") is True:
            values.append(value)
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            value = "待补充"
        if not isinstance(value, str):
            raise ValueError("each fill must be a string, null, or preserve directive")
        values.append(value)

    parts = []
    cursor = 0
    for (start, end), value in zip(spans, values):
        parts.append(template[cursor:start])
        if isinstance(value, dict):
            parts.append(template[start:end + 1])
        else:
            parts.append("[" + value + "]" if keep_brackets else value)
        cursor = end + 1
    parts.append(template[cursor:])
    return "".join(parts)


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("input must be a JSON object")
        unknown = set(payload) - {"template", "fills", "keep_brackets"}
        if unknown:
            raise ValueError("unknown input fields")
        result = fill_brackets(
            payload["template"],
            payload["fills"],
            payload.get("keep_brackets", True),
        )
    except (UnicodeError, json.JSONDecodeError, KeyError, ValueError) as error:
        print("Bracket completion failed: " + str(error), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(result.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
