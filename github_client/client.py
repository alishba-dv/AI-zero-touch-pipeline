"""GitHub API wrapper + git operations for pushing generated code as branches."""
from __future__ import annotations

import os
import subprocess

import requests

from config import Config
from utils.logger import get_logger

log = get_logger(__name__)

_API = "https://api.github.com"


class GitHubClient:
    def __init__(self) -> None:
        self._token = Config.GITHUB_TOKEN
        self._username = Config.GITHUB_USERNAME
        self._repo = Config.GITHUB_REPO
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ------------------------------------------------------------------
    # Repo management
    # ------------------------------------------------------------------

    def ensure_repo_exists(self) -> str:
        """Create the GitHub repo if it doesn't exist. Returns the clone URL."""
        url = f"{_API}/repos/{self._username}/{self._repo}"
        r = requests.get(url, headers=self._headers, timeout=15)

        if r.status_code == 200:
            log.info(f"[GITHUB] Repo {self._username}/{self._repo} already exists")
            return r.json()["clone_url"]

        if r.status_code == 404:
            log.info(f"[GITHUB] Creating repo {self._username}/{self._repo}")
            resp = requests.post(
                f"{_API}/user/repos",
                headers=self._headers,
                json={
                    "name": self._repo,
                    "description": "AI-generated code from Jira tickets — zero-touch pipeline",
                    "private": False,
                    "auto_init": True,  # creates initial commit so branches can be pushed
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["clone_url"]

        r.raise_for_status()
        return ""  # unreachable

    # ------------------------------------------------------------------
    # Branch push
    # ------------------------------------------------------------------

    def push_branch(self, workspace_path: str, branch_name: str, commit_message: str) -> str:
        """
        Initialise a fresh git repo in workspace_path, commit everything,
        and force-push it to GitHub as branch_name.
        Returns the URL of the branch on GitHub.
        """
        repo_url = (
            f"https://{self._username}:{self._token}"
            f"@github.com/{self._username}/{self._repo}.git"
        )

        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "AI Pipeline",
            "GIT_AUTHOR_EMAIL": "pipeline@ai-zero-touch.local",
            "GIT_COMMITTER_NAME": "AI Pipeline",
            "GIT_COMMITTER_EMAIL": "pipeline@ai-zero-touch.local",
        }

        def _run(*cmd: str) -> str:
            result = subprocess.run(
                list(cmd),
                cwd=workspace_path,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"git command failed: {' '.join(cmd)}\n{result.stderr}"
                )
            return result.stdout.strip()

        # Remove any existing git state so each push is clean
        git_dir = os.path.join(workspace_path, ".git")
        if os.path.exists(git_dir):
            import shutil
            shutil.rmtree(git_dir)

        _run("git", "init", "-b", "main")
        _run("git", "add", ".")
        _run("git", "commit", "-m", commit_message)
        _run("git", "push", repo_url, f"HEAD:{branch_name}", "--force")

        branch_url = (
            f"https://github.com/{self._username}/{self._repo}/tree/{branch_name}"
        )
        log.info(f"[GITHUB] Pushed branch: {branch_url}")
        return branch_url
