"""Main orchestrator — runs steps 1-9 in order."""
from __future__ import annotations

import os
import re
import sys

from config import Config
from jira_client.client import JiraClient
from utils.logger import get_logger
from workflow import (
    step1_pick_ticket,
    step2_download_requirements,
    step3_analyze_requirements,
    step4_implement_code,
    step5_generate_tests,
    step6_link_tests,
    step7_run_tests,
    step8_update_ticket,
    step9_push_github,
)

log = get_logger(__name__)


def _make_workspace_path(base: str, ticket_key: str, summary: str) -> str:
    """
    Return a descriptive workspace directory path, e.g.:
      workspace/SCRUM-5-build-basic-todo-application-with-crud-task-operations/
    """
    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")[:60].strip("-")
    dir_name = f"{ticket_key}-{slug}"
    path = os.path.join(base, dir_name)
    os.makedirs(path, exist_ok=True)
    return path


def run(project_key: str, project_root: str | None = None) -> int:
    """Execute the full workflow. Returns 0 on success, 1 on failure/blocked."""
    if project_root is None:
        project_root = os.getcwd()

    os.makedirs(Config.WORKSPACE_DIR, exist_ok=True)
    jira = JiraClient()

    # ── STEP 1 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 1 — Pick a ticket")
    ticket = step1_pick_ticket.run(project_key, jira)
    if ticket is None:
        return 0

    ticket_key: str = ticket["key"]
    ticket_summary: str = ticket["fields"].get("summary", ticket_key)
    ticket_jira_url = f"{Config.JIRA_URL}/browse/{ticket_key}"

    workspace_path = _make_workspace_path(Config.WORKSPACE_DIR, ticket_key, ticket_summary)
    log.info(f"Workspace: {workspace_path}")

    # ── STEP 2 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 2 — Download requirements.md")
    req_path = step2_download_requirements.run(ticket, jira, workspace_path)
    if req_path is None:
        return 1

    # ── STEP 3 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 3 — Analyse requirements")
    analysis_path = step3_analyze_requirements.run(ticket_key, req_path, workspace_path)

    # ── STEP 4 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 4 — Implement code")
    try:
        changed_files = step4_implement_code.run(
            ticket_key, analysis_path, project_root, workspace_path
        )
    except RuntimeError as exc:
        jira.add_comment(ticket_key, f"Blocking: build failed after retries.\n\n{exc}")
        log.error(f"[BLOCKED] {exc}")
        return 1

    # ── STEP 5 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 5 — Generate test cases")
    test_files, test_count = step5_generate_tests.run(
        ticket_key, analysis_path, changed_files, workspace_path, project_root
    )

    # ── STEP 6 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 6 — Link tests to Jira")
    linked_test_keys = step6_link_tests.run(ticket_key, workspace_path, project_key, jira)

    # ── STEP 7 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 7 — Run tests")
    test_result = step7_run_tests.run(ticket_key, test_files, changed_files, jira)

    if not test_result.all_pass:
        log.error(f"[BLOCKED] {ticket_key}: tests failed — ticket NOT marked Done")
        return 1

    # ── STEP 8 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 8 — Update Jira ticket to Done")
    step8_update_ticket.run(ticket_key, changed_files, test_count, linked_test_keys, jira)

    # ── STEP 9 ────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 9 — Push code to GitHub")
    try:
        branch_url = step9_push_github.run(
            ticket_key, ticket_summary, workspace_path, ticket_jira_url
        )
        log.info(f"Branch live at: {branch_url}")
    except Exception as exc:
        # GitHub push failure is non-fatal — ticket is already marked Done
        log.error(f"[GITHUB] Push failed (non-fatal): {exc}")

    log.info("=" * 60)
    log.info("Workflow complete.")
    return 0
