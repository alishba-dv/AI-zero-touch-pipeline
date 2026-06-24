# Analysis — SCRUM-5

# Requirements Analysis: To-Do Application

---

## 1. Functional Requirements

1. **Create Task** — Accept a `title` (required) and optional `description`; auto-assign a unique `id`, `createdAt` timestamp, and `status = "pending"`.
2. **List All Tasks** — Return all tasks with full metadata: `id`, `title`, `description`, `status`, `createdAt`.
3. **Update Task** — Allow updating `title`, `description`, and/or `status` for an existing task identified by `id`; reject updates to non-existent tasks.
4. **Delete Task** — Remove a task by `id`; return a meaningful error for unknown or invalid IDs.

---

## 2. Non-Functional Requirements

- **Simplicity** — Implementation must remain minimal (MVP scope); no over-engineering.
- **Maintainability** — Code structure should be clean and extensible for future enhancements (AI automation, external integrations).
- **Graceful error handling** — All invalid inputs (missing required fields, bad IDs) must produce clear error responses rather than crashes.
- **Data integrity** — `id` values must be unique across all tasks; timestamps must be system-generated (not user-supplied).

> No explicit performance, security, or scalability SLAs are defined — see Assumptions.

---

## 3. Inputs / Outputs / Data Contracts

### Task Model

```json
{
  "id":          "string | number  — system-assigned, unique, immutable",
  "title":       "string           — required, non-empty",
  "description": "string           — optional, may be null/absent",
  "status":      "\"pending\" | \"completed\"",
  "createdAt":   "ISO 8601 timestamp — system-assigned, immutable"
}
```

### Endpoint Contracts (assumed REST)

| Operation   | Input                              | Success Output                      | Error Output                        |
|-------------|-------------------------------------|--------------------------------------|--------------------------------------|
| Create Task | `{ title, description? }`          | Created task object (201)            | 400 if `title` missing/empty         |
| Read All    | _(none)_                           | Array of task objects (200)          | —                                    |
| Update Task | `id` (path) + `{ title?, description?, status? }` (body) | Updated task object (200) | 404 if not found; 400 if no valid fields |
| Delete Task | `id` (path)                        | Confirmation / 204 No Content        | 404 if not found; 400 if `id` invalid format |

---

## 4. Edge Cases & Error Conditions

| # | Scenario | Expected Behaviour |
|---|----------|--------------------|
| E1 | Create with empty or whitespace-only `title` | Reject with 400; do not persist |
| E2 | Create with no body / missing `title` field | Reject with 400 |
| E3 | Update with an `id` that does not exist | Return 404 |
| E4 | Delete with an `id` that does not exist | Return 404 |
| E5 | Delete with a malformed `id` (wrong type/format) | Return 400 |
| E6 | Update `status` to a value outside `pending\|completed` | Reject with 400 |
| E7 | Update with an empty body (no fields) | Reject with 400 (nothing to update) |
| E8 | Read when no tasks exist | Return empty array `[]`, not an error |
| E9 | Duplicate `title` on create | Allowed — uniqueness is enforced on `id` only |
| E10 | Attempt to update `id` or `createdAt` | Silently ignore or reject — these fields are immutable |

---

## 5. Acceptance Criteria

1. **AC-1 (Create):** `POST /tasks` with `{ "title": "Buy milk" }` returns a task object with a system-generated `id`, `createdAt`, and `status = "pending"`. HTTP 201.
2. **AC-2 (Create — validation):** `POST /tasks` with no `title` returns HTTP 400.
3. **AC-3 (Read):** `GET /tasks` returns an array containing all previously created tasks with all model fields present.
4. **AC-4 (Read — empty):** `GET /tasks` on an empty store returns `[]` with HTTP 200.
5. **AC-5 (Update):** `PUT/PATCH /tasks/{id}` with `{ "status": "completed" }` returns the updated task; subsequent `GET /tasks` reflects the change.
6. **AC-6 (Update — not found):** `PUT/PATCH /tasks/nonexistent` returns HTTP 404.
7. **AC-7 (Update — invalid status):** `PUT/PATCH /tasks/{id}` with `{ "status": "in-progress" }` returns HTTP 400.
8. **AC-8 (Delete):** `DELETE /tasks/{id}` returns HTTP 204; subsequent `GET /tasks` no longer includes that task.
9. **AC-9 (Delete — not found):** `DELETE /tasks/nonexistent` returns HTTP 404.
10. **AC-10 (Immutability):** `id` and `createdAt` values are identical before and after an update.

---

## 6. Assumptions

| # | Ambiguity | Assumed Default | Rationale |
|---|-----------|-----------------|-----------|
| A1 | `id` type is `"string-or-number"` | Use auto-incrementing integer or UUID string | UUID avoids collisions if persistence layer changes; document choice in code |
| A2 | No authentication/authorisation mentioned | No auth for MVP | Requirements state minimal MVP scope |
| A3 | No persistence backend specified | In-memory store (or file-backed) | Simplest implementation; swap for DB in future iteration |
| A4 | No `updatedAt` field in model | Omit for now | Not listed in the task model; can be added in a later iteration |
| A5 | `status` enum is only `pending\|completed` | Enforce strictly | Only two values shown; any others are invalid (AC-7) |
| A6 | No partial update (PATCH) vs full update (PUT) specified | Support PATCH semantics (only provided fields updated) | More natural for mobile/web clients; prevents accidental field erasure |
| A7 | No pagination or filtering on list endpoint | Return all tasks unfiltered | MVP scope; pagination is a future enhancement |
| A8 | No explicit HTTP framework specified | Implement with a lightweight REST framework appropriate to the project language | Defer to existing codebase conventions |
