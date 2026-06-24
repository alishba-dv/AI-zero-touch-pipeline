"""Thin wrapper around the `claude` CLI for AI-powered steps."""
from __future__ import annotations

import subprocess

from config import Config
from utils.logger import get_logger

log = get_logger(__name__)


def ask_claude(system: str, user: str) -> str:
    """Call the claude CLI and return its stdout response."""
    full_prompt = f"{system}\n\n{user}" if system else user

    result = subprocess.run(
        ["claude", "-p", full_prompt, "--model", Config.CLAUDE_MODEL],
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited with code {result.returncode}:\n{result.stderr}"
        )

    return result.stdout.strip()
