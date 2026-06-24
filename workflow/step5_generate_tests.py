"""STEP 5 — Generate test file + XRAY-compatible JSON using Claude Code."""
from __future__ import annotations

import json
import os
import re

from config import Config
from utils.claude_runner import ask_claude
from utils.logger import get_logger, log_test_cases_generated

log = get_logger(__name__)

_SYSTEM_TEST_CODE = """\
You are a senior QA engineer. Given requirements analysis and the implementation files,
generate a comprehensive test file.

Rules:
- Cover happy-path, edge cases, error/exception paths, and boundary values.
- Follow project conventions for the test framework.
- Output exactly one FILE: block with the test source:
  FILE: <relative/path/to/TestFile>
  ```<lang>
  // test code
  ```
"""

_SYSTEM_XRAY = """\
You are a QA engineer generating XRAY-compatible test case definitions.
Return a valid JSON array only — no surrounding text, no markdown fences.
Each element must have:
{
  "summary": "Short test name",
  "description": "What this test verifies",
  "steps": [
    { "action": "...", "data": "...", "expected_result": "..." }
  ],
  "labels": ["auto-generated"],
  "linked_issue": "<TICKET-KEY>"
}
"""


def _parse_single_file(response_text: str) -> tuple[str, str] | None:
    match = re.search(r"FILE:\s*(.+?)\n```[^\n]*\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2)
    return None


def run(
    ticket_key: str,
    analysis_path: str,
    changed_files: list[str],
    workspace_path: str,
    project_root: str,
) -> tuple[list[str], int]:
    with open(analysis_path, encoding="utf-8") as fh:
        analysis_text = fh.read()

    impl_snippets = ""
    for fp in changed_files[:5]:
        if os.path.isfile(fp):
            try:
                with open(fp, encoding="utf-8") as fh:
                    impl_snippets += f"\n\n### {fp}\n```\n{fh.read()[:3000]}\n```"
            except Exception:
                pass

    # --- Generate test source ---
    code_prompt = (
        f"Project root: {project_root}\n"
        f"Test directory: {Config.TEST_DIR}\n"
        f"Base package: {Config.BASE_PACKAGE}\n"
        f"Build tool: {Config.BUILD_TOOL}\n\n"
        f"Requirements analysis:\n{analysis_text}\n\n"
        f"Implementation files:{impl_snippets}\n\n"
        "Generate the test file."
    )

    code_response = ask_claude(_SYSTEM_TEST_CODE, code_prompt)
    parsed = _parse_single_file(code_response)

    test_files: list[str] = []
    if parsed:
        rel_path, code = parsed
        # Write to project test dir (for running)
        abs_path = os.path.join(project_root, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(code)
        test_files.append(abs_path)

        # Mirror into workspace/tests/<rel_path>
        ws_test_path = os.path.join(workspace_path, "tests", rel_path)
        os.makedirs(os.path.dirname(ws_test_path), exist_ok=True)
        with open(ws_test_path, "w", encoding="utf-8") as fh:
            fh.write(code)

    # --- Generate XRAY JSON ---
    xray_prompt = (
        f"Ticket key: {ticket_key}\n\n"
        f"Requirements analysis:\n{analysis_text}\n\n"
        "Generate the XRAY test case JSON array."
    )

    raw_xray = ask_claude(_SYSTEM_XRAY, xray_prompt)
    raw_xray = re.sub(r"^```[^\n]*\n?", "", raw_xray)
    raw_xray = re.sub(r"\n?```$", "", raw_xray)

    try:
        xray_cases: list[dict] = json.loads(raw_xray)
    except json.JSONDecodeError:
        log.warning("Invalid JSON from claude for XRAY cases; using empty list")
        xray_cases = []

    for tc in xray_cases:
        tc["linked_issue"] = ticket_key

    # Save XRAY JSON to workspace root
    xray_path = os.path.join(workspace_path, "xray_test_cases.json")
    with open(xray_path, "w", encoding="utf-8") as fh:
        json.dump(xray_cases, fh, indent=2)

    log_test_cases_generated(len(xray_cases))
    return test_files, len(xray_cases)
