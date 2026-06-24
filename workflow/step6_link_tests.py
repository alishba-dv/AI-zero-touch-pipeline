"""STEP 6 — Create Jira test issues for every entry in xray_test_cases.json."""
from __future__ import annotations

import json
import os

from jira_client.client import JiraClient
from utils.logger import get_logger, log_jira_test_linked

log = get_logger(__name__)


def run(ticket_key: str, workspace_path: str, project_key: str, jira: JiraClient) -> list[str]:
    xray_path = os.path.join(workspace_path, "xray_test_cases.json")

    if not os.path.isfile(xray_path):
        log.warning(f"xray_test_cases.json not found at {xray_path}; skipping step 6")
        return []

    with open(xray_path, encoding="utf-8") as fh:
        test_cases: list[dict] = json.load(fh)

    created_keys: list[str] = []
    for tc in test_cases:
        try:
            new_key = jira.create_test_issue(project_key, ticket_key, tc)
            created_keys.append(new_key)
            log_jira_test_linked(new_key, ticket_key)
        except Exception as exc:
            log.error(f"Failed to create test issue for '{tc.get('summary')}': {exc}")

    return created_keys
