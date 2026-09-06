"""Compare two benchmark result directories.

Examples:

    python3 benchmarks/create_diff.py
    python3 benchmarks/create_diff.py results/benchmarks/before results/benchmarks/after
    python3 benchmarks/create_diff.py results/benchmarks/before results/benchmarks/after -o /tmp/diff.json

Reports are paired by their stable suite suffix (``startup``,
``message-path`` or ``compare``), so the directories may use different run
tags. Numeric leaves are reported as ``a``, ``b``, ``delta`` and
``percent_change``. Other leaves retain both values and a changed flag.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path


KNOWN_SUITES = ("startup", "message-path", "compare")
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results" / "benchmarks"
DEFAULT_OUTPUT = Path.cwd() / "diff.json"


def discover_result_directories() -> list[Path]:
    """Return result directories from newest to oldest by filesystem time."""
    directories = [
        path for path in RESULTS_DIR.iterdir()
        if path.is_dir() and any(path.glob("*.json"))
    ]
    return sorted(
        directories,
        key=lambda path: (creation_time(path), path.name),
        reverse=True,
    )


def creation_time(path: Path) -> float:
    """Return filesystem birth time, falling back to inode change time."""
    stat = path.stat()
    return getattr(stat, "st_birthtime", stat.st_ctime)


def resolve_directories(a: Path | None, b: Path | None) -> tuple[Path, Path]:
    """Resolve omitted arguments to the latest two result directories."""
    if a is not None and b is not None:
        return a, b

    directories = discover_result_directories()
    if len(directories) < 2:
        raise ValueError(f"need at least two result directories in {RESULTS_DIR}")

    if a is None and b is None:
        return directories[1], directories[0]
    if b is None:
        latest = directories[0]
        if a.resolve() == latest.resolve():
            latest = directories[1]
        return a, latest
    return directories[1], b


def suite_name(path: Path, report: dict) -> str:
    """Return a stable name for a report despite run-specific prefixes."""
    stem = path.stem
    for suite in KNOWN_SUITES:
        if stem == suite or stem.endswith(f"-{suite}"):
            return suite
    return str(report.get("benchmark", stem)).lower()


def load_reports(directory: Path) -> dict[str, tuple[Path, dict]]:
    reports = {}
    for path in sorted(directory.glob("*.json")):
        with path.open() as stream:
            report = json.load(stream)
        name = suite_name(path, report)
        if name in reports:
            raise ValueError(f"multiple reports for suite {name!r} in {directory}")
        reports[name] = (path, report)
    return reports


def numeric_diff(a, b):
    delta = b - a
    if a == 0:
        percent_change = None
    else:
        percent_change = (delta / a) * 100
    return {
        "a": a,
        "b": b,
        "delta": delta,
        "percent_change": percent_change,
    }


def diff_value(a, b):
    """Recursively compare JSON values, using B minus A for numeric deltas."""
    if isinstance(a, bool) or isinstance(b, bool):
        return {"a": a, "b": b, "changed": a != b}
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not all(math.isfinite(value) for value in (a, b)):
            return {"a": a, "b": b, "changed": a != b}
        return numeric_diff(a, b)
    if isinstance(a, dict) and isinstance(b, dict):
        return {
            key: diff_value(a.get(key), b.get(key))
            for key in sorted(set(a) | set(b))
        }
    if isinstance(a, list) and isinstance(b, list):
        return {
            "a": a,
            "b": b,
            "changed": a != b,
        }
    return {"a": a, "b": b, "changed": a != b}


def compare_reports(before: Path, after: Path) -> dict:
    reports_a = load_reports(before)
    reports_b = load_reports(after)
    suites = sorted(set(reports_a) | set(reports_b))
    result = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "a": str(before),
        "b": str(after),
        "reports": {},
    }
    for suite in suites:
        item = {}
        if suite in reports_a:
            item["a_file"] = reports_a[suite][0].name
        if suite in reports_b:
            item["b_file"] = reports_b[suite][0].name
        if suite not in reports_a or suite not in reports_b:
            item["status"] = "missing_from_a" if suite not in reports_a else "missing_from_b"
        else:
            report_a = reports_a[suite][1]
            report_b = reports_b[suite][1]
            item["status"] = "matched"
            item["benchmark"] = diff_value(
                report_a.get("benchmarks", {}),
                report_b.get("benchmarks", {}),
            )
            item["metadata"] = {
                "generated_at": {"a": report_a.get("generated_at"), "b": report_b.get("generated_at")},
                "environment": diff_value(report_a.get("environment", {}), report_b.get("environment", {})),
                "options": diff_value(report_a.get("options", {}), report_b.get("options", {})),
            }
        result["reports"][suite] = item
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path, nargs="?", help="baseline benchmark directory (default: previous result)")
    parser.add_argument("b", type=Path, nargs="?", help="comparison benchmark directory (default: latest result)")
    parser.add_argument(
        "-o", "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"write JSON here (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)

    try:
        args.a, args.b = resolve_directories(args.a, args.b)
    except ValueError as error:
        parser.error(str(error))

    for directory in (args.a, args.b):
        if not directory.is_dir():
            parser.error(f"not a directory: {directory}")

    result = compare_reports(args.a, args.b)
    text = json.dumps(result, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(f"Saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())