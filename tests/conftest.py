"""A skipped test fails the check: a clone without the tree or tools must not pass by testing nothing. ALLOW_SKIP=1 allows it."""
import os


def pytest_runtest_logreport(report):
    if report.skipped and not os.environ.get("ALLOW_SKIP"):
        report.outcome = "failed"
