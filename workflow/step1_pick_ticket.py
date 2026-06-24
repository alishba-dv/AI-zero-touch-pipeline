"""STEP 1 — Pick the highest-priority To-Do ticket."""
from __future__ import annotations

from jira_client.client import JiraClient
from utils.logger import get_logger, log_done_no_tickets, log_ticket_selected

log = get_logger(__name__)


def run(project_key: str, jira: JiraClient) -> dict | None:
    tickets = jira.get_todo_tickets(project_key)

    if not tickets:
        log_done_no_tickets()
        return None

    ticket = tickets[0]
    key: str = ticket["key"]
    summary: str = ticket["fields"].get("summary", "(no summary)")
    log_ticket_selected(key, summary)
    return ticket
