# Claude Code — Jira Ticket Automation Workflow

You are an autonomous engineering agent. When invoked, you must execute the following workflow **end-to-end without pausing for confirmation**, unless a blocking ambiguity makes it impossible to proceed safely.

---

## Tools & Permissions You Have

- **Jira MCP** — read tickets, download attachments, create/link issues, update labels/status
- **Filesystem** — read and write files in the working directory
- **Shell / Bash** — run builds, tests, linters
- **Code editor** — create and modify source files

---

## Workflow — Execute Every Step in Order

### STEP 1 — Pick a Ticket

1. Query Jira for issues in the current project where **label = `To-Do`** and status is not `Done`.
2. Sort by priority (highest first), then by creation date (oldest first).
3. Select the **first** ticket from the result.
4. Log: `[TICKET SELECTED] <KEY> — <summary>`

> If no ticket matches, log `[DONE] No To-Do tickets found.` and exit.

---

### STEP 2 — Download `requirements.md`

1. Fetch all attachments on the selected ticket.
2. Find the file named **`requirements.md`** (case-insensitive).
3. Download it to `./workspace/<TICKET-KEY>/requirements.md`.
4. If the attachment is missing, check the ticket **description** — extract and save it as `requirements.md` instead.
5. Log: `[REQUIREMENTS] Saved to ./workspace/<TICKET-KEY>/requirements.md`

> If neither attachment nor description yields requirements, add a Jira comment:
> `"Blocking: requirements.md not found. Please attach or describe requirements."`,
> then exit.

---

### STEP 3 — Analyze Requirements

Read `./workspace/<TICKET-KEY>/requirements.md` thoroughly. Extract and document:

- **Functional requirements** — what the code must do
- **Non-functional requirements** — performance, security, constraints
- **Inputs / outputs / data contracts**
- **Edge cases and error conditions** explicitly called out
- **Acceptance criteria** (if present)

Save your analysis to `./workspace/<TICKET-KEY>/analysis.md`.

Log: `[ANALYSIS COMPLETE] ./workspace/<TICKET-KEY>/analysis.md`

---

### STEP 4 — Implement the Code

Using the analysis from Step 3:

1. Determine the correct **language, framework, and module location** from the existing codebase context.
2. Implement **all** functional requirements. Do not skip partial requirements.
3. Follow existing code conventions (naming, formatting, package structure).
4. Add inline comments for non-obvious logic.
5. Place output files in the appropriate source directories (not the workspace scratch folder).
6. Run the build (`mvn clean compile` for Maven / equivalent for other tools) and fix any compile errors before continuing.

Log: `[IMPLEMENTATION COMPLETE] Files changed: <list of files>`

---

### STEP 5 — Generate Test Cases

1. Create a test file covering:
   - All happy-path scenarios from the requirements
   - All edge cases identified in analysis
   - All error/exception paths
   - Boundary value cases
2. Name the file following project conventions (e.g., `<ClassName>Test.java`).
3. Place it in the correct test source directory.
4. Separately, generate an **XRAY-compatible test case list** in JSON format at
   `./workspace/<TICKET-KEY>/xray_test_cases.json`
   with this structure per test:

```json
[
  {
    "summary": "Short test name",
    "description": "What this test verifies",
    "steps": [
      { "action": "...", "data": "...", "expected_result": "..." }
    ],
    "labels": ["auto-generated"],
    "linked_issue": "<TICKET-KEY>"
  }
]
```

Log: `[TEST CASES GENERATED] <count> test cases`

---

### STEP 6 — Link Test Cases to the Jira Ticket

1. For each entry in `xray_test_cases.json`, create a **Jira sub-task or Test issue** (use XRAY issue type `Test` if available, otherwise `Sub-task`).
2. Set the **parent/linked issue** to `<TICKET-KEY>`.
3. Populate summary, description, and steps from the JSON.
4. Log each created issue: `[JIRA TEST LINKED] <TEST-KEY> → <TICKET-KEY>`

---

### STEP 7 — Execute the Test Cases

Run the full test suite scoped to the new implementation:

```bash
# Maven example — adjust for your build tool
mvn test -pl <module> -Dtest=<TestClassName>
```

Capture the output. Parse results:

- **PASS** — test method succeeded
- **FAIL** — test method failed (log method name + failure message)
- **ERROR** — test threw an unexpected exception

If **any test fails**:
1. Attempt to fix the implementation (not the test).
2. Re-run. Repeat up to **3 fix-and-retry cycles**.
3. If still failing after 3 cycles, add a Jira comment with the failure details and **do not mark the ticket Done** — exit with status `BLOCKED`.

Log: `[TEST RESULTS] Passed: X | Failed: Y | Errors: Z`

---

### STEP 8 — Update the Jira Ticket Label to Done

Only if **all tests pass**:

1. Remove the label `To-Do` from the ticket.
2. Add the label `Done`.
3. Transition the ticket status to **Done** (or the equivalent closing status in your workflow).
4. Add a Jira comment summarising the work:

```
✅ Automated implementation complete.

- Requirements analysed: ./workspace/<KEY>/analysis.md
- Files changed: <list>
- Test cases generated: <count>
- Test results: All passed
- Linked test issues: <TEST-KEY-1>, <TEST-KEY-2>, ...
```

Log: `[TICKET CLOSED] <TICKET-KEY> moved to Done`

---

## Error Handling Rules

| Situation | Action |
|---|---|
| No To-Do ticket found | Log and exit cleanly |
| `requirements.md` missing | Comment on ticket, exit |
| Build fails after implementation | Fix and retry; if 3 attempts fail, comment and exit |
| Tests fail after 3 retries | Comment failure details, do NOT close ticket |
| Jira API error | Log error with response body, exit |
| Ambiguous requirement | Make a reasonable assumption, document it in `analysis.md`, proceed |

---

## Constraints

- **Never** modify test files to make tests pass — fix the implementation.
- **Never** mark a ticket Done if any test is failing or erroring.
- **Always** commit or save code changes before running tests.
- **Always** keep `./workspace/<TICKET-KEY>/` as the scratch directory; source code goes in its proper project location.
- **Do not** ask for user input mid-workflow unless a true blocker is encountered (missing requirements, auth failure).

---

## Invocation

Run this agent with:

```bash
claude --model claude-sonnet-4-6 \
       --mcp-config mcp_config.json \
       -p "Execute the Jira ticket automation workflow defined in CLAUDE.md for project <PROJECT-KEY>"
```

Where `mcp_config.json` configures your Jira MCP server connection.

---

*This file is the single source of truth for the automation agent. Keep it in the repo root.*
