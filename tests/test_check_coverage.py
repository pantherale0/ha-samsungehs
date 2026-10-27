"""The coverage gate checks each file and never substitutes aggregate coverage."""

import pytest

from scripts.check_coverage import check_coverage


@pytest.mark.parametrize(
    ("module", "covered", "total", "passed"),
    [
        ("sensor.py", 96, 100, True),
        ("sensor.py", 95, 100, False),
        ("sensor.py", 94, 100, False),
        ("config_flow.py", 99, 100, False),
        ("config_flow.py", 100, 100, True),
        ("diagnostics.py", 99, 100, False),
        ("diagnostics.py", 100, 100, True),
        ("__init__.py", 0, 0, True),
    ],
)
def test_threshold(module: str, covered: int, total: int, *, passed: bool) -> None:
    """Boundary values enforce strict HA line targets, independent of branches."""
    report = {
        "files": {
            module: {
                "summary": {
                    "covered_lines": covered,
                    "num_statements": total,
                    "percent_covered": 0,
                }
            }
        }
    }
    assert (check_coverage(report, [module]) == []) is passed


def test_missing_module() -> None:
    """An entirely unimported or omitted module cannot escape enforcement."""
    assert check_coverage({"files": {}}, ["sensor.py"]) == [
        "sensor.py: missing from coverage report"
    ]


def test_per_file() -> None:
    """High coverage elsewhere cannot compensate for an untested module."""
    report = {
        "files": {
            "sensor.py": {"summary": {"covered_lines": 10000, "num_statements": 10000}},
            "services.py": {"summary": {"covered_lines": 0, "num_statements": 1}},
        }
    }
    assert check_coverage(report, ["sensor.py", "services.py"]) == [
        "services.py: 0.00%, requires more than 95% line coverage"
    ]
