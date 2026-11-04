"""A skipped test fails the check: a clone without the tree or tools must not pass by testing nothing. ALLOW_SKIP=1 allows it."""
import os

import pytest


@pytest.hookimpl(hookwrapper=True)  # at creation: by the logreport hook, pytest may already have counted the failures
def pytest_runtest_makereport(item, call):
    report = (yield).get_result()
    if report.skipped and not os.environ.get("ALLOW_SKIP"):
        report.outcome = "failed"
