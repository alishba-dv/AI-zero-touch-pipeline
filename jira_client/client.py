"""Thin wrapper around the Jira REST API v3 (Jira Cloud)."""
from __future__ import annotations

import os
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from config import Config
from utils.logger import get_logger

log = get_logger(__name__)

PRIORITY_ORDER = {
    "Highest": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Lowest": 4,
}


class JiraClient:
    def __init__(self) -> None:
        self._base = Config.JIRA_URL.rstrip("/")
        self._auth = HTTPBasicAuth(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
        self._headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._base}{path}"
        resp = requests.get(url, auth=self._auth, headers=self._headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> Any:
        url = f"{self._base}{path}"
        resp = requests.post(url, auth=self._auth, headers=self._headers, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def _put(self, path: str, body: dict) -> Any:
        url = f"{self._base}{path}"
        resp = requests.put(url, auth=self._auth, headers=self._headers, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # ------------------------------------------------------------------
    # Step 1 — ticket selection
    # ------------------------------------------------------------------

    def get_todo_tickets(self, project_key: str) -> list[dict]:
        """Return open (To Do / In Progress) issues not yet Done, sorted by priority then age."""
        jql = (
            f'project = "{project_key}" AND status not in (Done, Closed, Resolved) '
            f'ORDER BY priority ASC, created ASC'
        )
        data = self._get(
            "/rest/api/3/search/jql",
            params={
                "jql": jql,
                "maxResults": 50,
                "fields": "summary,priority,created,labels,attachment,description,status,issuetype",
            },
        )
        issues = data.get("issues", [])

        def sort_key(issue: dict) -> tuple[int, str]:
            priority_name = (issue["fields"].get("priority") or {}).get("name", "Medium")
            created = issue["fields"].get("created", "")
            return (PRIORITY_ORDER.get(priority_name, 99), created)

        return sorted(issues, key=sort_key)

    # ------------------------------------------------------------------
    # Step 2 — attachments / description
    # ------------------------------------------------------------------

    def get_attachments(self, ticket_key: str) -> list[dict]:
        issue = self._get(
            f"/rest/api/3/issue/{ticket_key}",
            params={"fields": "attachment"},
        )
        return issue["fields"].get("attachment", [])

    def download_attachment(self, attachment: dict, dest_path: str) -> None:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        resp = requests.get(attachment["content"], auth=self._auth, timeout=60)
        resp.raise_for_status()
        with open(dest_path, "wb") as fh:
            fh.write(resp.content)

    def get_issue_description(self, ticket_key: str) -> str | None:
        """Return plain-text description (handles both v3 ADF and plain string)."""
        issue = self._get(
            f"/rest/api/3/issue/{ticket_key}",
            params={"fields": "description"},
        )
        desc = issue["fields"].get("description")
        if desc is None:
            return None
        # v3 returns ADF (Atlassian Document Format) — extract plain text
        if isinstance(desc, dict):
            return _adf_to_text(desc)
        return str(desc)

    # ------------------------------------------------------------------
    # Step 6 — create test / sub-task issues
    # ------------------------------------------------------------------

    def get_issue_types(self, project_key: str) -> list[dict]:
        data = self._get(f"/rest/api/3/project/{project_key}/statuses")
        # Fall back to createmeta for issue types
        meta = self._get(
            "/rest/api/3/issue/createmeta",
            params={"projectKeys": project_key, "expand": "projects.issuetypes"},
        )
        projects = meta.get("projects", [])
        if projects:
            return projects[0].get("issuetypes", [])
        return []

    def create_test_issue(self, project_key: str, parent_key: str, test: dict) -> str:
        """Create a Sub-task (or Test if XRAY available) linked to parent_key."""
        issue_types = self.get_issue_types(project_key)
        type_names = {t["name"].lower(): t["name"] for t in issue_types}
        issue_type = type_names.get("test") or type_names.get("sub-task") or "Task"

        steps_text = "\n".join(
            f"- {s.get('action', '')} | data: {s.get('data', '')} | expected: {s.get('expected_result', '')}"
            for s in test.get("steps", [])
        )
        description_text = f"{test.get('description', '')}\n\nSteps:\n{steps_text}"

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": test["summary"],
                "description": _text_to_adf(description_text),
                "issuetype": {"name": issue_type},
                "labels": test.get("labels", ["auto-generated"]),
            }
        }

        if issue_type.lower() == "sub-task":
            payload["fields"]["parent"] = {"key": parent_key}

        created = self._post("/rest/api/3/issue", payload)
        new_key: str = created["key"]

        if issue_type.lower() != "sub-task":
            for link_type in ("Relates", "relates to", "Relate", "Tests"):
                try:
                    self._post(
                        "/rest/api/3/issueLink",
                        {
                            "type": {"name": link_type},
                            "inwardIssue": {"key": new_key},
                            "outwardIssue": {"key": parent_key},
                        },
                    )
                    break
                except Exception as exc:
                    log.debug(f"Link type '{link_type}' failed for {new_key} → {parent_key}: {exc}")
            else:
                log.warning(f"Could not link {new_key} → {parent_key}: no valid link type found")

        return new_key

    # ------------------------------------------------------------------
    # Step 8 — update ticket
    # ------------------------------------------------------------------

    def get_transitions(self, ticket_key: str) -> list[dict]:
        data = self._get(f"/rest/api/3/issue/{ticket_key}/transitions")
        return data.get("transitions", [])

    def transition_to_done(self, ticket_key: str) -> None:
        transitions = self.get_transitions(ticket_key)
        done_transition = next(
            (
                t for t in transitions
                if t["name"].lower() in ("done", "close", "closed", "resolve", "resolved")
            ),
            None,
        )
        if done_transition:
            self._post(
                f"/rest/api/3/issue/{ticket_key}/transitions",
                {"transition": {"id": done_transition["id"]}},
            )
        else:
            log.warning(f"No 'Done' transition found for {ticket_key}; skipping status change")

    def update_labels(self, ticket_key: str, remove: list[str], add: list[str]) -> None:
        issue = self._get(
            f"/rest/api/3/issue/{ticket_key}",
            params={"fields": "labels"},
        )
        current_labels: list[str] = issue["fields"].get("labels", [])
        new_labels = [lbl for lbl in current_labels if lbl not in remove] + add
        self._put(f"/rest/api/3/issue/{ticket_key}", {"fields": {"labels": new_labels}})

    def add_comment(self, ticket_key: str, body: str) -> None:
        self._post(
            f"/rest/api/3/issue/{ticket_key}/comment",
            {"body": _text_to_adf(body)},
        )


# ------------------------------------------------------------------
# ADF helpers (Atlassian Document Format used by v3 API)
# ------------------------------------------------------------------

def _text_to_adf(text: str) -> dict:
    """Wrap plain text in a minimal ADF document."""
    paragraphs = []
    for line in text.split("\n"):
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line or " "}],
        })
    return {"type": "doc", "version": 1, "content": paragraphs}


def _adf_to_text(node: dict) -> str:
    """Recursively extract plain text from an ADF node."""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = []
    for child in node.get("content", []):
        parts.append(_adf_to_text(child))
    return "\n".join(p for p in parts if p)
