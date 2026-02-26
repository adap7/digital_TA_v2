# Issue 13: Exercise Create/Edit Hardening

## Status: TODO

---

## Goal

The exercise create (`POST /api/v1/courses/{id}/exercises/`) and edit
(`PATCH /api/v1/exercises/{id}/`) endpoints work, but have two real
security/correctness gaps:

1. **Audit fields are writable** — `ExerciseTeacherSerializer` uses
   `fields="__all__"`, making `status`, `created_by`, `reviewed_by`, and
   `published_at` writable. Teachers should never set these directly; they
   go through workflow endpoints or are auto-set by the view.

2. **Model validation not called** — `Exercise.clean()` validates MCQ
   type/choices consistency and tenant safety, but neither `perform_create`
   nor `perform_update` calls `full_clean()`. A teacher can create an MCQ
   without choices, or a free-text exercise with choices, and the DB accepts it.

Additionally, `order_index` conflicts currently crash with a raw
`IntegrityError` instead of a clean 400 response.

---

## Serializer Changes (`courses/serializers.py`)

**New: `ExerciseWriteSerializer`** — used for POST and PATCH input.
Only exposes fields a teacher is allowed to set:

```python
class ExerciseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            "topic", "title", "type", "prompt",
            "choices", "answer_key", "difficulty", "order_index",
        ]
```

Excluded (read-only / auto-set):
`course`, `created_by`, `reviewed_by`, `status`, `published_at`,
`created_at`, `updated_at`

**`ExerciseTeacherSerializer`** stays unchanged (read-only GET responses).

---

## View Changes (`courses/views.py`)

### `CourseExerciseListView`
- Use `ExerciseWriteSerializer` for POST (create) input
- After `serializer.save(...)` in `perform_create()`:
  - Call `instance.full_clean()` to enforce model validation
  - Wrap in `try/except DjangoValidationError` → return 400
  - Wrap in `try/except IntegrityError` (order_index conflict) → return 400

### `ExerciseDetailView`
- Use `ExerciseWriteSerializer` for PATCH input
- After save in `perform_update()`:
  - Call `instance.full_clean()` → 400 on violation

GET responses still use `ExerciseTeacherSerializer` (full read visibility).

---

## Tests to Add (`courses/tests/test_exercises.py`)

| Test | Expected |
|------|----------|
| Create MCQ without choices | 400 |
| Create free-text with choices | 400 |
| PATCH MCQ type to free-text without removing choices | 400 |
| PATCH `status` directly | field ignored (status unchanged) |
| PATCH `created_by` directly | field ignored (created_by unchanged) |
| Create two exercises with same `order_index` | 400, clear error message |

---

## Files to Modify

| File | Change |
|------|--------|
| `courses/serializers.py` | Add `ExerciseWriteSerializer` |
| `courses/views.py` | Use write serializer for input; call `full_clean()`; handle `IntegrityError` |
| `courses/tests/test_exercises.py` | Add 6 new tests |

No new models or migrations needed.

---

## Acceptance Criteria

- [ ] Teachers cannot PATCH `status`, `created_by`, `reviewed_by`, or `published_at`
- [ ] Creating an MCQ without `choices` returns 400
- [ ] Creating a free-text exercise with `choices` returns 400
- [ ] Duplicate `order_index` within a course returns 400 with a readable message
- [ ] All existing 25 exercise tests still pass
- [ ] 6 new tests pass
