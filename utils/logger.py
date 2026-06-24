import logging
import sys
from config import Config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
    return logger


# Convenience helpers that emit the bracketed log tags the spec requires
_root = get_logger("pipeline")


def log(msg: str) -> None:
    _root.info(msg)


def log_ticket_selected(key: str, summary: str) -> None:
    log(f"[TICKET SELECTED] {key} — {summary}")


def log_requirements(key: str) -> None:
    log(f"[REQUIREMENTS] Saved to ./workspace/{key}/requirements.md")


def log_analysis_complete(key: str) -> None:
    log(f"[ANALYSIS COMPLETE] ./workspace/{key}/analysis.md")


def log_implementation_complete(files: list[str]) -> None:
    log(f"[IMPLEMENTATION COMPLETE] Files changed: {', '.join(files)}")


def log_test_cases_generated(count: int) -> None:
    log(f"[TEST CASES GENERATED] {count} test cases")


def log_jira_test_linked(test_key: str, ticket_key: str) -> None:
    log(f"[JIRA TEST LINKED] {test_key} → {ticket_key}")


def log_test_results(passed: int, failed: int, errors: int) -> None:
    log(f"[TEST RESULTS] Passed: {passed} | Failed: {failed} | Errors: {errors}")


def log_ticket_closed(key: str) -> None:
    log(f"[TICKET CLOSED] {key} moved to Done")


def log_done_no_tickets() -> None:
    log("[DONE] No To-Do tickets found.")
