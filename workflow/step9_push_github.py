"""STEP 9 — Push generated code to GitHub as a branch named after the Jira ticket."""
from __future__ import annotations

from github_client.client import GitHubClient
from utils.logger import get_logger

log = get_logger(__name__)


def run(
    ticket_key: str,
    ticket_summary: str,
    workspace_path: str,
    jira_url: str,
) -> str:
    gh = GitHubClient()

    gh.ensure_repo_exists()

    commit_message = (
        f"feat({ticket_key}): {ticket_summary}\n\n"
        f"Automated implementation by AI zero-touch pipeline.\n"
        f"Jira ticket: {jira_url}"
    )

    branch_url = gh.push_branch(workspace_path, ticket_key, commit_message)
    log.info(f"[GITHUB PUSH] {ticket_key} → {branch_url}")
    return branch_url
