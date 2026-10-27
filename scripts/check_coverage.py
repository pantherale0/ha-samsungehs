"""Enforce HA's per-module line coverage targets on a coverage.py JSON report."""

import argparse
import json
from pathlib import Path


def check_coverage(report: dict, modules: list[str]) -> list[str]:
    """Return failures, including modules absent from the coverage report."""
    failures = []
    for module in modules:
        if (file_report := report["files"].get(module)) is None:
            failures.append(f"{module}: missing from coverage report")
            continue
        summary = file_report["summary"]
        statements = summary["num_statements"]
        if not statements:
            continue
        covered = summary["covered_lines"]
        percent = covered * 100 / statements
        if Path(module).name in {"config_flow.py", "diagnostics.py"}:
            if covered != statements:
                failures.append(
                    f"{module}: {percent:.2f}%, requires 100% line coverage"
                )
        elif covered * 100 <= statements * 95:
            failures.append(
                f"{module}: {percent:.2f}%, requires more than 95% line coverage"
            )
    return failures


def main() -> int:
    """Check all integration source modules, including unimported files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report", type=Path, help="coverage JSON produced by pytest --cov"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    modules = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "custom_components/samsungehs").glob("*.py")
    )
    failures = check_coverage(json.loads(args.report.read_text()), modules)
    for failure in failures:
        print(failure)
    if failures:
        return 1
    print(f"Coverage passed for {len(modules)} integration modules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
