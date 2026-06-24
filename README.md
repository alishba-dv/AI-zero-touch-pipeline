# AI Zero-Touch Pipeline

An autonomous engineering agent that takes a Jira ticket from **To-Do → Done** with zero human intervention. It reads requirements, generates production code with Claude, writes and runs tests, links everything back to Jira, and pushes the result to GitHub — all in a single command.

---

## How It Works

```
Jira ticket (To-Do)
        │
        ▼
 STEP 1  Pick highest-priority To-Do ticket
        │
        ▼
 STEP 2  Download requirements.md from attachment (or ticket description)
        │
        ▼
 STEP 3  Analyse requirements → analysis.md
        │
        ▼
 STEP 4  Generate implementation with Claude → compile → fix loop (max 3x)
        │
        ▼
 STEP 5  Generate test cases + xray_test_cases.json
        │
        ▼
 STEP 6  Create Jira sub-tasks / Test issues, link to parent ticket
        │
        ▼
 STEP 7  Run test suite → fix loop (max 3x)
        │
        ▼
 STEP 8  Transition ticket to Done, post summary comment on Jira
        │
        ▼
 STEP 9  Push branch to GitHub
        │
        ▼
Jira ticket (Done) + GitHub branch + linked test issues
```

---

## Project Structure

```
AI-zero-touch-pipeline/
├── main.py                        # CLI entry point
├── config.py                      # Centralised config (reads .env)
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
├── mcp_config.json                # MCP server config (Jira)
│
├── workflow/                      # One module per pipeline step
│   ├── orchestrator.py            # Runs steps 1-9 in order
│   ├── step1_pick_ticket.py       # Query Jira for highest-priority To-Do
│   ├── step2_download_requirements.py  # Fetch requirements.md
│   ├── step3_analyze_requirements.py   # Claude: analyse → analysis.md
│   ├── step4_implement_code.py    # Claude: implement → build → retry
│   ├── step5_generate_tests.py    # Claude: test file + xray_test_cases.json
│   ├── step6_link_tests.py        # Create Jira test issues, link to ticket
│   ├── step7_run_tests.py         # Run suite → Claude fix → retry
│   ├── step8_update_ticket.py     # Label Done, transition, comment
│   └── step9_push_github.py      # Push workspace branch to GitHub
│
├── jira_client/
│   └── client.py                  # Jira REST API v3 wrapper
│
├── github_client/
│   └── client.py                  # GitHub API + git push helper
│
├── utils/
│   ├── claude_runner.py           # Thin wrapper around `claude` CLI
│   └── logger.py                  # Structured log tags (e.g. [TICKET SELECTED])
│
├── workspace/                     # Scratch directory — one folder per ticket
│   └── <TICKET-KEY>-<slug>/
│       ├── requirements.md
│       ├── analysis.md
│       ├── xray_test_cases.json
│       └── implementation/        # Mirror of generated source files
│
└── src/                           # Java source tree (target project)
    ├── main/java/com/example/app/
    └── test/java/com/example/app/
```

---

## Pipeline Steps in Detail

### Step 1 — Pick a Ticket
Queries Jira with JQL for all open issues not in `Done / Closed / Resolved`. Sorts by priority (Highest → Lowest) then by creation date (oldest first). Picks the first result.

### Step 2 — Download Requirements
Looks for a file attachment named `requirements.md` (case-insensitive). Falls back to the ticket description if no attachment is found. Saves to `workspace/<KEY>/requirements.md`.

### Step 3 — Analyse Requirements
Sends `requirements.md` to Claude with instructions to extract:
- Functional and non-functional requirements
- Input/output data contracts
- Edge cases and error conditions
- Acceptance criteria and assumptions

Output saved to `workspace/<KEY>/analysis.md`.

### Step 4 — Implement Code
Sends `analysis.md` to Claude with the project root, source directory, base package, and build tool. Claude returns `FILE: <path>` blocks which are written to the correct source locations and mirrored under `workspace/<KEY>/implementation/`. Runs `mvn clean compile` (or equivalent) after each attempt. Retries up to 3 times on build failure, feeding the error output back to Claude each cycle.

### Step 5 — Generate Test Cases
Claude generates a test class covering all happy paths, edge cases, and error conditions from the analysis. Also produces `workspace/<KEY>/xray_test_cases.json` — an XRAY-compatible list of test cases with steps, descriptions, and labels.

### Step 6 — Link Tests to Jira
For each entry in `xray_test_cases.json`, creates a Jira issue (type `Test` if XRAY is available, otherwise `Sub-task` or `Task`). Sub-tasks are parented directly; other types are linked via `issueLink` (tries `"Relates"`, `"relates to"`, `"Relate"`, `"Tests"` in order).

### Step 7 — Run Tests
Runs the full test suite (`mvn test` or equivalent). Parses stdout/stderr for pass/fail/error counts. On failure, sends the **tail** of the output (where actual errors appear) plus current implementation files to Claude for a fix. Retries up to 3 cycles. If still failing, posts a comment on the Jira ticket and exits without marking Done.

### Step 8 — Update Ticket
Removes the `To-Do` label, adds `Done`, transitions the ticket to the Done status, and posts a summary comment listing changed files, test count, and linked test issue keys.

### Step 9 — Push to GitHub
Initialises a fresh git repo inside the workspace folder, commits all generated artifacts, and force-pushes to a branch named after the ticket key (e.g. `SCRUM-5`) on the configured GitHub repository. Creates the repo automatically if it doesn't exist.

---

## Setup

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Java | 17+ |
| Maven | 3.8+ |
| Claude Code CLI | latest (`npm install -g @anthropic-ai/claude-code`) |
| Git | any recent |

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:

| Variable | Description |
|----------|-------------|
| `JIRA_URL` | Your Jira Cloud base URL (e.g. `https://yoursite.atlassian.net`) |
| `JIRA_EMAIL` | Atlassian account email |
| `JIRA_API_TOKEN` | Jira API token from id.atlassian.com |
| `GITHUB_TOKEN` | GitHub personal access token (needs `repo` scope) |
| `GITHUB_USERNAME` | GitHub username |

Optional variables (have defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_KEY` | `PROJ` | Jira project key |
| `BUILD_TOOL` | `maven` | `maven`, `gradle`, `npm`, `pytest`, or `make` |
| `BUILD_MODULE` | `.` | Maven module path relative to project root |
| `SRC_DIR` | `src/main/java` | Source directory |
| `TEST_DIR` | `src/test/java` | Test directory |
| `BASE_PACKAGE` | `com.example.app` | Java base package for generated code |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `GITHUB_REPO` | `AI-zero-touch-pipeline` | GitHub repo name |

---

## Running the Pipeline

```bash
python main.py <PROJECT_KEY>
```

Example:

```bash
python main.py SCRUM
```

Optional — override the project root (where source files are written):

```bash
python main.py SCRUM --root /path/to/your/java/project
```

The pipeline is fully autonomous. It will:
1. Pick the first open To-Do ticket in the SCRUM project
2. Implement and test the feature
3. Update the Jira ticket
4. Push a branch to GitHub

---

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| No To-Do ticket found | Logs `[DONE] No To-Do tickets found.` and exits cleanly (code 0) |
| `requirements.md` missing | Comments on the ticket and exits (code 1) |
| Build fails after 3 retries | Comments failure details on ticket, exits blocked (code 1) |
| Tests fail after 3 retries | Comments failure details on ticket, does NOT close ticket |
| GitHub push fails | Non-fatal — ticket is already marked Done, push failure is logged |
| Jira issueLink 404 | Falls back through multiple link-type names; warns if all fail |

---

## Key Design Decisions

- **Tail of test output, not head** — Maven downloads fill the first N kilobytes of output; actual errors are at the end. `step7_run_tests.py` passes `output[-4000:]` to Claude.
- **Claude CLI timeout is 600 s** — Maven dependency downloads on a cold cache can exceed 5 minutes. The fix-prompt call in `claude_runner.py` uses a 600-second timeout to avoid false timeouts.
- **Issue link type fallback** — Jira link-type names are instance-specific. The client tries `"Relates"`, `"relates to"`, `"Relate"`, `"Tests"` in order so the pipeline works across different Jira configurations.
- **Workspace isolation** — All scratch files go under `workspace/<TICKET-KEY>-<slug>/`. Source code goes in its proper location in the project tree so the build tools find it.
- **Never modify tests** — If tests fail, Claude is instructed to fix the implementation only, never the test file.

---

## SCRUM-5 — Build Basic To-Do Application with CRUD Task Operations

This was the first ticket processed by the pipeline. See the [SCRUM-5 branch](../../tree/SCRUM-5) for the generated output.

### Ticket Summary

**Key:** SCRUM-5  
**Summary:** Build Basic To-Do Application with CRUD Task Operations  
**Status:** Done (closed by the pipeline)

### What Was Built

A Spring Boot 3.3 REST API implementing full CRUD for tasks, running on an in-memory store.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tasks` | Create a task (`title` required, `description` optional) |
| `GET` | `/tasks` | List all tasks |
| `PATCH` | `/tasks/{id}` | Update `title`, `description`, and/or `status` |
| `DELETE` | `/tasks/{id}` | Delete a task by ID |

**Task model:**

```json
{
  "id":          "UUID string — system-assigned",
  "title":       "string — required, non-empty",
  "description": "string — optional",
  "status":      "pending | completed",
  "createdAt":   "ISO 8601 timestamp — system-assigned"
}
```

**Validation rules enforced:**
- `title` missing or blank → 400
- `status` outside `pending | completed` → 400
- Update with empty body → 400
- Update or delete of non-existent ID → 404
- Malformed ID format (special characters) → 400
- `id` and `createdAt` are immutable (ignored on update)

### Generated Files

| File | Purpose |
|------|---------|
| `src/main/java/com/example/app/TodoApplication.java` | Spring Boot entry point |
| `src/main/java/com/example/app/Task.java` | Task entity (POJO) |
| `src/main/java/com/example/app/TaskRepository.java` | Repository interface |
| `src/main/java/com/example/app/InMemoryTaskRepository.java` | In-memory `ConcurrentHashMap` implementation |
| `src/main/java/com/example/app/TaskController.java` | REST controller — all four endpoints |
| `src/main/java/com/example/app/CreateTaskRequest.java` | Request DTO for POST |
| `src/main/java/com/example/app/UpdateTaskRequest.java` | Request DTO for PATCH |
| `src/main/java/com/example/app/ErrorResponse.java` | Uniform error response body |
| `src/test/java/com/example/app/TaskControllerTest.java` | Generated test class (20 test cases) |

### Workspace Artifacts

All pipeline artifacts for SCRUM-5 are stored under:

```
workspace/SCRUM-5-build-basic-to-do-application-with-crud-task-operations/
├── requirements.md          # Original requirements from Jira attachment
├── analysis.md              # Claude's structured analysis
├── xray_test_cases.json     # 20 XRAY-compatible test cases
└── implementation/          # Mirror of all generated source files
```

### Jira Linked Test Issues

20 sub-tasks / test issues were created and linked to SCRUM-5 (SCRUM-46 through SCRUM-65), covering:
- Happy-path create, read, update, delete
- Validation: missing title, blank title, invalid status, empty update body
- Edge cases: empty task list, immutable fields, duplicate titles, non-existent IDs
- Boundary: malformed ID format

---

## Dependencies

**Python (`requirements.txt`):**

| Package | Purpose |
|---------|---------|
| `requests` | HTTP calls to Jira and GitHub REST APIs |
| `python-dotenv` | Load `.env` into environment |
| `jira` | Optional higher-level Jira client (REST calls use `requests` directly) |

**External tools:**
- `claude` CLI — code generation and fix cycles
- `mvn` — build and test execution
- `git` — branch creation and push in Step 9
