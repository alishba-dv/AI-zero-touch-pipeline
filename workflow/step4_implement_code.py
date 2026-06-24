"""STEP 4 — Generate and write the implementation using Claude Code."""
from __future__ import annotations

import os
import shutil
import subprocess

from config import Config
from utils.claude_runner import ask_claude
from utils.logger import get_logger, log_implementation_complete

log = get_logger(__name__)

_SYSTEM = """\
You are a senior software engineer. Given a requirements analysis you must produce
complete, production-quality source code.

Rules:
- Output ONLY valid source code files — no commentary outside of code blocks.
- Respond with one or more fenced code blocks, each preceded by a line:
  FILE: <relative/path/to/file>
  followed immediately by the code block, e.g.:

  FILE: src/main/java/com/example/app/Calculator.java
  ```java
  // ... code ...
  ```

- Follow existing project conventions for the language/framework.
- Add inline comments only for non-obvious logic.
- Cover all functional requirements — do not skip any.
"""


def _parse_files(response_text: str) -> dict[str, str]:
    files: dict[str, str] = {}
    lines = response_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("FILE:"):
            rel_path = line[len("FILE:"):].strip()
            i += 1
            if i < len(lines) and lines[i].strip().startswith("```"):
                i += 1
                code_lines: list[str] = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                files[rel_path] = "\n".join(code_lines)
        i += 1
    return files


def _run_build(build_tool: str, module: str) -> tuple[bool, str]:
    commands = {
        "maven": ["mvn", "clean", "compile"] + ([f"-pl{module}"] if module != "." else []) + ["-q"],
        "gradle": ["./gradlew", "compileJava"],
        "npm": ["npm", "run", "build"],
        "pytest": ["python3", "-m", "py_compile"],
        "make": ["make"],
    }
    cmd = [c for c in commands.get(build_tool, ["echo", "no-build"]) if c]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0, result.stdout + result.stderr
    except FileNotFoundError as exc:
        return False, str(exc)
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 120 seconds"


def _copy_to_workspace(rel_path: str, code: str, workspace_path: str) -> None:
    """Mirror the generated file into workspace/<ticket>/implementation/<rel_path>."""
    dest = os.path.join(workspace_path, "implementation", rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(code)


def run(ticket_key: str, analysis_path: str, project_root: str, workspace_path: str) -> list[str]:
    with open(analysis_path, encoding="utf-8") as fh:
        analysis_text = fh.read()

    user_prompt = (
        f"Project root: {project_root}\n"
        f"Source directory: {Config.SRC_DIR}\n"
        f"Base package: {Config.BASE_PACKAGE}\n"
        f"Build tool: {Config.BUILD_TOOL}\n\n"
        f"Requirements analysis:\n\n{analysis_text}\n\n"
        "Generate the complete implementation using FILE: <path> blocks."
    )

    changed_files: list[str] = []

    for attempt in range(1, Config.MAX_FIX_RETRIES + 1):
        response = ask_claude(_SYSTEM, user_prompt)
        parsed = _parse_files(response)

        if not parsed:
            log.warning("No FILE: blocks found — writing raw response as placeholder")
            placeholder_rel = os.path.join(Config.SRC_DIR, "generated_output.txt")
            placeholder_abs = os.path.join(project_root, placeholder_rel)
            os.makedirs(os.path.dirname(placeholder_abs), exist_ok=True)
            with open(placeholder_abs, "w", encoding="utf-8") as fh:
                fh.write(response)
            _copy_to_workspace(placeholder_rel, response, workspace_path)
            changed_files = [placeholder_abs]
            break

        changed_files = []
        for rel_path, code in parsed.items():
            abs_path = os.path.join(project_root, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as fh:
                fh.write(code)
            _copy_to_workspace(rel_path, code, workspace_path)
            changed_files.append(abs_path)

        success, build_output = _run_build(Config.BUILD_TOOL, Config.BUILD_MODULE)
        if success:
            break

        log.warning(f"Build failed (attempt {attempt}/{Config.MAX_FIX_RETRIES}):\n{build_output}")

        if attempt == Config.MAX_FIX_RETRIES:
            raise RuntimeError(
                f"Build failed after {Config.MAX_FIX_RETRIES} attempts.\n{build_output}"
            )

        user_prompt = (
            f"The build failed with these errors:\n\n{build_output}\n\n"
            "Fix the implementation. Return corrected FILE: blocks only."
        )

    log_implementation_complete(changed_files)
    return changed_files
