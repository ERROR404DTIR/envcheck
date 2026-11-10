#!/usr/bin/env python3
"""envcheck - compare a .env file against .env.example (zero dependencies)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

__version__ = "1.0.0"

LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def _clean(value: str) -> str:
    """Strip quotes and trailing inline comments from a raw value."""
    value = value.strip()
    if value[:1] in ("'", '"'):
        quote = value[0]
        end = value.find(quote, 1)
        return value[1:end] if end != -1 else value[1:]
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def parse_env(text: str):
    """Return (values, duplicate_keys, invalid_line_numbers)."""
    values: dict[str, str] = {}
    duplicates: list[str] = []
    invalid: list[int] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = LINE_RE.match(raw)
        if not match:
            invalid.append(number)
            continue
        key, value = match.group(1), _clean(match.group(2))
        if key in values:
            duplicates.append(key)
        values[key] = value
    return values, duplicates, invalid


def compare(env_text: str, example_text: str) -> dict:
    env, duplicates, invalid = parse_env(env_text)
    example, _, _ = parse_env(example_text)
    return {
        "missing": sorted(k for k in example if k not in env),
        "empty": sorted(k for k, v in env.items() if v == ""),
        "duplicates": sorted(set(duplicates)),
        "extra": sorted(k for k in env if k not in example),
        "invalid": invalid,
    }


SECTIONS = [
    ("missing", "31", "✘ Missing from env file"),
    ("duplicates", "33", "! Duplicate keys"),
    ("empty", "33", "! Empty values"),
    ("invalid", "31", "✘ Invalid lines (line numbers)"),
    ("extra", "36", "+ Not in example file"),
]


def render(report: dict, color: bool) -> str:
    def paint(code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    lines = []
    for key, code, title in SECTIONS:
        items = report[key]
        if items:
            lines.append(paint(code, f"{title} ({len(items)})"))
            lines.extend(f"    {item}" for item in items)
    if not lines:
        return paint("32", "✔ All good: your env file matches the example.")
    return "\n".join(lines)


def exit_code(report: dict, strict: bool) -> int:
    errors = report["missing"] or report["duplicates"] or report["invalid"]
    warnings = report["empty"] or report["extra"]
    return 1 if errors or (strict and warnings) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envcheck",
        description="Compare a .env file against .env.example.",
    )
    parser.add_argument("--env", default=".env", help="env file (default: .env)")
    parser.add_argument(
        "--example", default=".env.example", help="example file (default: .env.example)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="treat empty and extra keys as errors"
    )
    parser.add_argument(
        "--fix", action="store_true", help="append missing keys to the env file"
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--no-color", action="store_true", help="disable colors")
    parser.add_argument("--version", action="version", version=f"envcheck {__version__}")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    env_path, example_path = Path(args.env), Path(args.example)
    for path in (env_path, example_path):
        if not path.is_file():
            print(f"envcheck: file not found: {path}", file=sys.stderr)
            return 2

    env_text = env_path.read_text(encoding="utf-8")
    example_text = example_path.read_text(encoding="utf-8")
    report = compare(env_text, example_text)

    if args.fix and report["missing"]:
        example_values, _, _ = parse_env(example_text)
        with env_path.open("a", encoding="utf-8") as handle:
            if env_text and not env_text.endswith("\n"):
                handle.write("\n")
            for key in report["missing"]:
                handle.write(f"{key}={example_values[key]}\n")
        print(f"envcheck: added {len(report['missing'])} missing key(s) to {env_path}")
        report = compare(env_path.read_text(encoding="utf-8"), example_text)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        color = not args.no_color and sys.stdout.isatty()
        print(render(report, color))
    return exit_code(report, args.strict)


if __name__ == "__main__":
    sys.exit(main())
