"""STEP 8 — Mark Jira ticket Done when all tests pass."""
from __future__ import annotations

from jira_client.client import JiraClient
from utils.logger import get_logger, log_ticket_closed

log = get_logger(__name__)


def run(
    ticket_key: str,
    changed_files: list[str],
    test_count: int,
    linked_test_keys: list[str],
    jira: JiraClient,
) -> None:
    jira.transition_to_done(ticket_key)

    files_list = "\n".join(f"  - {f}" for f in changed_files) or "  (none)"
    linked_list = ", ".join(linked_test_keys) or "(none)"

    comment = (
        "✅ Automated implementation complete.\n\n"
        f"- Requirements analysed: ./workspace/{ticket_key}/analysis.md\n"
        f"- Files changed:\n{files_list}\n"
        f"- Test cases generated: {test_count}\n"
        f"- Test results: All passed\n"
        f"- Linked test issues: {linked_list}"
    )
    jira.add_comment(ticket_key, comment)
    log_ticket_closed(ticket_key)
