# Analysis — SCRUM-5

# Requirements Analysis — To-Do Application

## 1. Functional Requirements

1. **Create Task** — Accept a `title` (required) and optional `description`; persist a new task record with a system-assigned unique `id`, `createdAt` timestamp, and `status` defaulted to `"pending"`.
2. **List Tasks** — Return all stored tasks including full metadata (`id`, `title`, `description`, `status`, `createdAt`).
3. **Update Task** — Accept a task `id` plus one or more mutable fields (`title`, `description`, `status`); verify the task exists before applying changes.
4. **Delete Task** — Accept a task `id`; remove the matching record; return a graceful error response when the `id` is invalid or not found.
5. **Status Constraint** — `status` field must only accept the values `"pending"` or `"completed"`.

---

## 2. Non-Functional Requirements

- **Simplicity** — Code must be minimal and readable; no over-engineering (MVP scope).
- **Maintainability** — Structure must support future extension (e.g., additional statuses, AI integration, external workflows) without rearchitecting core CRUD.
- **Graceful Error Handling** — All invalid inputs and missing-resource conditions must return structured error responses rather than unhandled exceptions.
- **Data Integrity** — IDs must be unique across all tasks; no two tasks may share the same `id`.

> No explicit performance SLAs, authentication, or persistence backend are specified (see Assumptions).

---

## 3. Inputs / Outputs / Data Contracts

### Task Model

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `string` or `number` | System-assigned | Unique; generated on create |
| `title` | `string` | Yes | Non-empty |
| `description` | `string` | No | Defaults to `null` / omitted |
| `status` | `"pending"` \| `"completed"` | System-assigned on create | Mutable via update |
| `createdAt` | ISO 8601 timestamp | System-assigned | Immutable after creation |

### Create Task — Input
```json
{ "title": "string (required)", "description": "string (optional)" }
```

### Create Task — Output
```json
{ "id": "...", "title": "...", "description": "...", "status": "pending", "createdAt": "..." }
```

### List Tasks — Output
```json
[ { "id": "...", "title": "...", "description": "...", "status": "...", "createdAt": "..." } ]
```

### Update Task — Input
```json
{ "title": "string (optional)", "description": "string (optional)", "status": "pending|completed (optional)" }
```

### Update Task — Output
Updated task object (same shape as Create output).

### Delete Task — Input
Task `id` (path parameter or request body).

### Delete Task — Output
Confirmation message or `204 No Content`; error object on failure.

---

## 4. Edge Cases & Error Conditions

| Condition | Expected Behaviour |
|---|---|
| Create with missing `title` | Reject with validation error; do not persist |
| Create with empty string `title` | Reject — treat as missing |
| Update with non-existent `id` | Return `404`-equivalent error |
| Delete with non-existent `id` | Return graceful error; do not throw |
| Delete with malformed `id` (wrong type) | Return graceful error |
| Update `status` to an invalid value (e.g., `"in-progress"`) | Reject with validation error |
| Update with no fields provided | Reject or no-op with informative message |
| List when no tasks exist | Return empty array `[]`, not an error |
| Duplicate `id` on create (if IDs are caller-supplied) | Reject with conflict error |
| `createdAt` supplied by caller on create | Ignore; always system-assigned |

---

## 5. Acceptance Criteria

1. **Create** — Given a valid `title`, a task is persisted and returned with a unique `id`, `status = "pending"`, and a non-null `createdAt`.
2. **Create — validation** — Given no `title` or an empty `title`, the system rejects the request and no task is stored.
3. **List** — Calling list returns every previously created (non-deleted) task with all metadata fields present.
4. **List empty** — Calling list on an empty store returns `[]` without error.
5. **Update** — Given a valid `id` and at least one mutable field, the task is updated and the updated object is returned.
6. **Update — not found** — Given an unknown `id`, the system returns an error and no data is modified.
7. **Update — invalid status** — Given `status = "in-progress"`, the system rejects the request.
8. **Delete** — Given a valid `id`, the task is removed and is no longer returned by list.
9. **Delete — not found** — Given an unknown or malformed `id`, the system returns a graceful error without crashing.
10. **Status immutability of `createdAt`** — `createdAt` cannot be changed via an update call.

---

## 6. Assumptions

| # | Ambiguity | Assumed Default |
|---|---|---|
| A1 | Persistence backend not specified | In-memory store (e.g., a Map/array); swap-out for a DB in later iterations |
| A2 | API style not specified | RESTful HTTP endpoints (standard for CRUD MVPs) |
| A3 | `id` generation strategy not specified | UUID v4 or auto-incrementing integer assigned server-side |
| A4 | Authentication/authorisation not mentioned | None required for MVP |
| A5 | `updatedAt` field not listed in the model | Omitted from MVP model; can be added when needed |
| A6 | Pagination for list endpoint not mentioned | Return all tasks (no limit); add pagination in a future iteration |
| A7 | `description` default when omitted | Stored as `null` / excluded from response JSON |
| A8 | Concurrent write safety not mentioned | Not required for MVP; single-process, single-thread assumed |
