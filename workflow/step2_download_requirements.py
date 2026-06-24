"""STEP 2 — Download requirements.md from the Jira ticket."""
from __future__ import annotations

import os

from jira_client.client import JiraClient
from utils.logger import get_logger, log_requirements

log = get_logger(__name__)


def run(ticket: dict, jira: JiraClient, workspace_path: str) -> str | None:
    """workspace_path is the pre-created per-ticket directory (e.g. workspace/SCRUM-5-slug/)."""
    key: str = ticket["key"]
    os.makedirs(workspace_path, exist_ok=True)
    dest_path = os.path.join(workspace_path, "requirements.md")

    attachments = jira.get_attachments(key)
    req_attachment = next(
        (a for a in attachments if a["filename"].lower() == "requirements.md"),
        None,
    )

    if req_attachment:
        jira.download_attachment(req_attachment, dest_path)
        log_requirements(key)
        return dest_path

    description = jira.get_issue_description(key)
    if description and description.strip():
        with open(dest_path, "w", encoding="utf-8") as fh:
            fh.write(f"# Requirements — {key}\n\n{description}\n")
        log_requirements(key)
        return dest_path

    jira.add_comment(
        key,
        "Blocking: requirements.md not found. Please attach or describe requirements.",
    )
    log.error(f"[BLOCKED] No requirements found for {key}. Commented on ticket.")
    return None
