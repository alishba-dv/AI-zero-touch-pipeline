"""STEP 3 — Analyse requirements.md with Claude Code and save analysis.md."""
from __future__ import annotations

import os

from utils.claude_runner import ask_claude
from utils.logger import get_logger, log_analysis_complete

log = get_logger(__name__)

_SYSTEM = """\
You are a senior software engineer performing requirements analysis.
Given a requirements document, extract and structure the following sections:

1. **Functional Requirements** — numbered list of what the code must do
2. **Non-Functional Requirements** — performance, security, scalability constraints
3. **Inputs / Outputs / Data Contracts** — types, formats, schemas
4. **Edge Cases & Error Conditions** — explicit and implicit
5. **Acceptance Criteria** — testable pass/fail conditions
6. **Assumptions** — any ambiguities you resolved with a reasonable default

Return a well-structured Markdown document with these exact sections.
"""


def run(ticket_key: str, requirements_path: str, workspace_path: str) -> str:
    with open(requirements_path, encoding="utf-8") as fh:
        requirements_text = fh.read()

    analysis = ask_claude(
        _SYSTEM,
        f"Analyse these requirements and produce the structured analysis:\n\n{requirements_text}",
    )

    analysis_path = os.path.join(workspace_path, "analysis.md")
    with open(analysis_path, "w", encoding="utf-8") as fh:
        fh.write(f"# Analysis — {ticket_key}\n\n{analysis}\n")

    log_analysis_complete(ticket_key)
    return analysis_path
