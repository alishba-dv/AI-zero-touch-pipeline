#!/usr/bin/env python3
"""Entry point for the AI zero-touch pipeline."""
import argparse
import sys

from workflow.orchestrator import run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous Jira ticket → implementation → test → Done pipeline"
    )
    parser.add_argument(
        "project_key",
        help="Jira project key (e.g. PROJ)",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Project root directory (defaults to current working directory)",
    )
    args = parser.parse_args()

    exit_code = run(args.project_key, args.root)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
