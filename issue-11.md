# Issue 11: Teacher Manual Review of Submissions

## Status: COMPLETE ✓

---

## Goal

Teachers (assigned to the course) and admins can manually review an AI-graded
submission: leave a written comment and optionally override the AI's correctness
verdict. Students see the teacher's comment and verdict alongside the AI result.

The AI grading is **never deleted** — `is_correct` stays unchanged.

---

## Data Model (done — migration 0009)

Fields added to `Submission` in `courses/models.py`:

| Field | Type | Notes |
|-------|------|-------|
| `teacher_comment` | TextField, blank=True, default="" | Written feedback |
| `teacher_is_correct` | BooleanField, null=True | Human override of AI verdict |
| `reviewed_by` | FK → User, SET_NULL, null=True | Who reviewed |
| `reviewed_at` | DateTimeField, null=True | When reviewed |

---

## API (done)

| Method | URL | Who | Description |
|--------|-----|-----|-------------|
| `PATCH` | `/api/v1/submissions/{id}/review/` | Teacher (assigned) / Admin | Submit review |

### Request body
```json
{
  "teacher_comment": "Good reasoning, but the sign is wrong.",
  "teacher_is_correct": false
}
```
Both fields optional. `teacher_is_correct` may be omitted (null = no verdict override).

---

## Serializers (done)

- `SubmissionReviewSerializer` — write input: `teacher_comment`, `teacher_is_correct`
- `SubmissionTeacherSerializer` — includes all four teacher review fields
- `SubmissionSerializer` (student-facing) — includes `teacher_comment` + `teacher_is_correct` only (no `reviewed_by` / `reviewed_at`)

---

## Permissions (done)

| Actor | PATCH /submissions/{id}/review/ |
|-------|---------------------------------|
| Admin (same tenant) | 200 |
| Teacher (assigned to course) | 200 |
| Teacher (unassigned) | 403 |
| Student | 403 |
| Cross-tenant | 404 |

---

## Tests (done — `courses/tests/test_review.py`, 9 tests)

- [x] Assigned teacher can review (comment + verdict)
- [x] `reviewed_by` and `reviewed_at` auto-set
- [x] Partial review (comment only, no verdict)
- [x] Admin can review any submission in tenant
- [x] Student cannot review → 403
- [x] Unassigned teacher cannot review → 403
- [x] Cross-tenant → 404
- [x] Re-review overwrites previous values
- [x] Student sees `teacher_comment` in GET /submissions/{id}/ ; `reviewed_by` absent