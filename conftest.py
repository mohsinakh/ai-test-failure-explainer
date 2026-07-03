"""
Shared pytest fixtures and hooks for the TestMu SDET-1 suite.

LLM integration (Task 3, Option A - Failure Explainer):
Whenever a test fails, `pytest_runtest_makereport` below gathers whatever
state is available - traceback, the page's URL/visible text for UI tests,
or the raw HTTP response for API tests - and sends it to a local model via
`llm_integration.failure_explainer.explain_failure`. The explanation is a
plain-English root cause + suggested fix. It's attached to the pytest-html
report as an "AI Failure Analysis" section and appended to
reports/failure_explanations.md.

Report handling (added after the first few runs kept overwriting each
other): `pytest_configure` below archives the previous run's HTML report
before pytest-html writes a fresh one, and drops a timestamped separator
into failure_explanations.md so multiple runs' worth of AI analysis stay
easy to tell apart in one growing log. See "How reports work" in README.md.
"""
import os
import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

from llm_integration.failure_explainer import explain_failure

load_dotenv()

REPORTS_DIR = Path(__file__).parent / "reports"
FAILURE_LOG = REPORTS_DIR / "failure_explanations.md"


# ---------------------------------------------------------------------------
# Report archiving
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Runs once, before any tests, before pytest-html writes anything.

    If --html was passed (this repo's README always uses
    reports/report.html) and a report already exists there from a
    previous run, move it into reports/archive/ first, named after when
    THAT run actually finished (its file mtime), not the current time.
    pytest-html then writes this run's fresh report to reports/report.html
    as normal - "latest" is always at the same familiar path, and nothing
    from a previous run is ever silently lost.
    """
    htmlpath = config.getoption("htmlpath", default=None)
    if htmlpath:
        _archive_previous_report(Path(htmlpath))

    _write_run_separator()


def _archive_previous_report(report_path: Path):
    if not report_path.exists():
        return  # first run ever, or archiving already handled it - nothing to do

    archive_dir = report_path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    finished_at = datetime.datetime.fromtimestamp(report_path.stat().st_mtime)
    stamp = finished_at.strftime("%Y-%m-%d_%H-%M-%S")

    dest = archive_dir / f"{report_path.stem}_{stamp}{report_path.suffix}"
    suffix_n = 1
    while dest.exists():  # extremely unlikely, but don't clobber on a same-second collision
        dest = archive_dir / f"{report_path.stem}_{stamp}_{suffix_n}{report_path.suffix}"
        suffix_n += 1

    report_path.rename(dest)


def _write_run_separator():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(FAILURE_LOG, "a") as f:
        f.write(f"\n---\n# Run started {datetime.datetime.now().isoformat()}\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_context():
    """Mutable dict API tests use to stash their last request/response so
    the failure explainer has something concrete to look at if the test
    fails. UI tests don't need this - we read the Playwright `page`
    fixture directly instead (see below)."""
    return {}


# ---------------------------------------------------------------------------
# Failure explainer hook
# ---------------------------------------------------------------------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    context = {
        "test_name": item.nodeid,
        "error": str(call.excinfo.value) if call.excinfo else "Unknown error",
        "traceback": str(call.excinfo.getrepr(style="short")) if call.excinfo else "",
    }

    # UI tests: pull whatever we still can from the live Playwright page.
    page = item.funcargs.get("page")
    if page is not None:
        try:
            context["url"] = page.url
            context["page_text_snippet"] = page.locator("body").inner_text()[:1500]
        except Exception:
            pass  # page may already be torn down; best-effort only

    # API tests: pull the last response the test stashed for us.
    api_ctx = item.funcargs.get("api_context")
    if api_ctx:
        context["api_context"] = api_ctx

    try:
        explanation = explain_failure(context)
    except Exception as e:
        explanation = f"_LLM failure explainer raised an exception: {e}_"

    _attach_to_html_report(report, explanation)
    _write_to_log(context["test_name"], explanation)


def _attach_to_html_report(report, explanation: str):
    try:
        from pytest_html import extras
    except ImportError:
        return
    if not hasattr(report, "extra"):
        report.extra = []
    report.extra.append(extras.text(explanation, name="AI Failure Analysis"))


def _write_to_log(test_name: str, explanation: str):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(FAILURE_LOG, "a") as f:
        f.write(f"\n## {test_name}\n_{datetime.datetime.now().isoformat()}_\n\n{explanation}\n\n---\n")