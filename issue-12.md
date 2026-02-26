# Issue 12: Student Progress Endpoint

## Status: TODO

---

## Goal

Give students, teachers, and admins a summary of a student's progress through a
course: how many exercises they've attempted, their correct rate, and a breakdown
per topic. This powers the dashboard view on the frontend.

---

## Business Rules

1. **Latest attempt only** — if a student submitted 3 times on exercise X, only
   the submission with the highest `attempt_number` counts.
2. **Effective correctness** — `teacher_is_correct` overrides `is_correct` (AI grade).
   If both are null → not yet graded → counts as attempted but not correct.
3. **Exercises counted** — only `PUBLISHED` exercises in the course.
4. **Topics** — exercises without a topic are grouped under `"Uncategorised"` (`topic_id: null`).

---

## API

| Method | URL | Who | Description |
|--------|-----|-----|-------------|
| `GET` | `/api/v1/courses/{id}/progress/` | Student (own) / Teacher (assigned) / Admin | Course-level progress |

### Query param
- `?student=<id>` — teacher or admin only; returns progress for that specific student.
  Omitting it: student gets their own, teacher/admin get an aggregate across all enrolled students.

---

## Response: single student

```json
{
  "course_id": 3,
  "student_id": 7,
  "total_exercises": 12,
  "attempted": 8,
  "correct": 5,
  "correct_rate": 0.625,
  "topics": [
    {
      "topic_id": 1,
      "topic_title": "Derivatives",
      "total_exercises": 4,
      "attempted": 4,
      "correct": 3
    },
    {
      "topic_id": null,
      "topic_title": "Uncategorised",
      "total_exercises": 4,
      "attempted": 2,
      "correct": 1
    }
  ]
}
```

`correct_rate` = correct / attempted (0 if attempted == 0).

---

## Response: aggregate (teacher/admin, no `?student` param)

```json
{
  "course_id": 3,
  "enrolled_students": 25,
  "average_correct_rate": 0.71,
  "topics": [
    {
      "topic_id": 1,
      "topic_title": "Derivatives",
      "average_correct_rate": 0.80
    },
    {
      "topic_id": null,
      "topic_title": "Uncategorised",
      "average_correct_rate": 0.60
    }
  ]
}
```

---

## Permissions

| Actor | Behaviour |
|-------|-----------|
| Student (enrolled) | Gets own progress only; 403 if not enrolled |
| Student + `?student=<id>` | 403 |
| Teacher (assigned) | Gets aggregate or single student via `?student=<id>` |
| Teacher (unassigned) | 403 |
| Admin (same tenant) | Gets aggregate or single student via `?student=<id>` |
| Cross-tenant | 404 |

---

## View (`courses/views.py`)

New: `CourseProgressView` (APIView, GET only).

Key query pattern — latest attempt per exercise per student:
```python
from django.db.models import Max, Subquery, OuterRef

latest_submissions = Submission.objects.filter(
    exercise__course=course,
    exercise__status=Exercise.Status.PUBLISHED,
    student=student,
    attempt_number=Subquery(
        Submission.objects.filter(
            exercise=OuterRef("exercise"),
            student=student,
        ).values("exercise").annotate(max=Max("attempt_number")).values("max")
    ),
)
```

Effective correctness helper:
```python
def _effective_correct(submission):
    if submission.teacher_is_correct is not None:
        return submission.teacher_is_correct
    return submission.is_correct  # may still be None
```

---

## URL wiring (`courses/urls.py`)

```python
path("<int:course_id>/progress/", CourseProgressView.as_view()),
```

---

## Files to Modify / Create

| File | Change |
|------|--------|
| `courses/views.py` | Add `CourseProgressView` |
| `courses/urls.py` | Add `<course_id>/progress/` path |
| `courses/tests/test_progress.py` | New — 10 tests |

No new models or migrations needed.

---

## Tests (`courses/tests/test_progress.py`)

| Test | Expected |
|------|----------|
| Student gets own progress for enrolled course | 200, correct totals |
| Only latest attempt counts (not all attempts) | `attempted` = 1 even with 3 submissions |
| `teacher_is_correct` overrides AI `is_correct` | effective grade uses teacher verdict |
| Ungraded submission counts as attempted, not correct | `correct` does not increment |
| Student cannot use `?student=<id>` | 403 |
| Student not enrolled → 403 | 403 |
| Teacher (assigned) can query `?student=<id>` | 200 |
| Teacher (unassigned) → 403 | 403 |
| Admin gets aggregate (no `?student`) | 200, `enrolled_students` count correct |
| Cross-tenant course → 404 | 404 |

---

## Acceptance Criteria

- [ ] `GET /api/v1/courses/{id}/progress/` returns per-topic breakdown for a student
- [ ] Only latest attempt per exercise counts
- [ ] `teacher_is_correct` takes precedence over `is_correct`
- [ ] Students cannot query other students' progress
- [ ] Teacher/admin aggregate mode works without `?student` param
- [ ] Teacher/admin single-student mode works with `?student=<id>`
- [ ] All 10 tests pass
