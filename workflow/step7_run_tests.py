"""STEP 7 — Run tests; attempt up to MAX_FIX_RETRIES fix cycles on failure."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field

from config import Config
from jira_client.client import JiraClient
from utils.claude_runner import ask_claude
from utils.logger import get_logger, log_test_results

log = get_logger(__name__)

_FIX_SYSTEM = (
    "You are a senior engineer fixing a failing implementation. "
    "Output FILE: <path> blocks followed by fenced code, one per file changed. "
    "Never modify test files — only fix the implementation."
)


@dataclass
class TestResult:
    passed: int = 0
    failed: int = 0
    errors: int = 0
    failures: list[dict] = field(default_factory=list)

    @property
    def all_pass(self) -> bool:
        return self.failed == 0 and self.errors == 0


def _build_test_command(build_tool: str, module: str, test_class: str | None) -> list[str]:
    if build_tool == "maven":
        cmd = ["mvn", "test"]
        if module != ".":
            cmd += ["-pl", module]
        if test_class:
            cmd += [f"-Dtest={test_class}"]
        return cmd
    if build_tool == "gradle":
        cmd = ["./gradlew", "test"]
        if test_class:
            cmd += [f"--tests={test_class}"]
        return cmd
    if build_tool == "npm":
        return ["npm", "test", "--", "--ci"]
    if build_tool == "pytest":
        return ["python3", "-m", "pytest", "-v"]
    return ["make", "test"]


def _parse_results(output: str) -> TestResult:
    result = TestResult()

    m = re.search(r"Tests run:\s*(\d+).*?Failures:\s*(\d+).*?Errors:\s*(\d+)", output, re.DOTALL)
    if m:
        total = int(m.group(1))
        result.failed = int(m.group(2))
        result.errors = int(m.group(3))
        result.passed = total - result.failed - result.errors
        return result

    m = re.search(r"(\d+) passed", output)
    if m:
        result.passed = int(m.group(1))
    m = re.search(r"(\d+) failed", output)
    if m:
        result.failed = int(m.group(1))
    m = re.search(r"(\d+) error", output)
    if m:
        result.errors = int(m.group(1))

    for match in re.finditer(r"FAILED\s+(.+?)(?:\n|$)", output):
        result.failures.append({"method": match.group(1).strip(), "message": ""})

    return result


def _attempt_fix(failure_output: str, changed_files: list[str]) -> None:
    impl_snippets = ""
    for fp in changed_files:
        try:
            with open(fp, encoding="utf-8") as fh:
                impl_snippets += f"\n\nFILE: {fp}\n```\n{fh.read()[:3000]}\n```"
        except Exception:
            pass

    fix_prompt = (
        f"The tests failed with these errors:\n\n{failure_output[-4000:]}\n\n"
        f"Current implementation files:{impl_snippets}\n\n"
        "Fix the implementation (NOT the tests). "
        "Return only FILE: blocks for files that need changes."
    )

    response = ask_claude(_FIX_SYSTEM, fix_prompt)

    for match in re.finditer(r"FILE:\s*(.+?)\n```[^\n]*\n(.*?)```", response, re.DOTALL):
        abs_path = match.group(1).strip()
        code = match.group(2)
        try:
            with open(abs_path, "w", encoding="utf-8") as fh:
                fh.write(code)
            log.info(f"  Fixed: {abs_path}")
        except Exception as exc:
            log.warning(f"  Could not write fix to {abs_path}: {exc}")


def run(
    ticket_key: str,
    test_files: list[str],
    changed_files: list[str],
    jira: JiraClient,
) -> TestResult:
    test_class: str | None = None
    if test_files:
        test_class = re.sub(r"\.(java|kt|py|ts|js)$", "", test_files[0].split("/")[-1])

    for attempt in range(1, Config.MAX_FIX_RETRIES + 1):
        cmd = _build_test_command(Config.BUILD_TOOL, Config.BUILD_MODULE, test_class)
        log.info(f"Running tests (attempt {attempt}): {' '.join(cmd)}")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            output = proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            output = "Test run timed out after 300 seconds"

        result = _parse_results(output)
        log_test_results(result.passed, result.failed, result.errors)

        if result.all_pass:
            return result

        log.warning(f"Tests did not all pass — attempting fix #{attempt}")

        if attempt == Config.MAX_FIX_RETRIES:
            failure_summary = (
                f"Tests failed after {Config.MAX_FIX_RETRIES} fix attempts.\n\n"
                f"Passed: {result.passed} | Failed: {result.failed} | Errors: {result.errors}\n\n"
                f"Output (last 3000 chars):\n{output[-3000:]}"
            )
            jira.add_comment(ticket_key, failure_summary)
            log.error(f"[BLOCKED] {ticket_key}: {failure_summary}")
            return result

        _attempt_fix(output, changed_files)

    return result
