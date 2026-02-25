## Goal

Allow teachers and admins to manually review AI-graded student submissions,
override the correctness verdict, and leave a written comment. Students can
see the teacher's comment after review. This closes the feedback loop between
AI-generated feedback and human teacher judgment.



## Scope

- Extend Submission with teacher review fields
- PATCH endpoint for teachers/admins to review a submission
- Students can read teacher comments on their own submissions
- Teacher review does not remove the AI messages — both coexist
- Tenant + course assignment safety enforced



## Data model

- [ ] Add fields to `Submission` model:

&nbsp; - [ ] `teacher_comment` (TextField, blank=True, default="")

&nbsp; - [ ] `teacher_is_correct` (BooleanField, null=True, blank=True —
             teacher's verdict; None means not yet reviewed)

&nbsp; - [ ] `reviewed_by` (FK → User, null=True, blank=True, SET_NULL —
             which teacher performed the review)

&nbsp; - [ ] `reviewed_at` (DateTimeField, null=True, blank=True —
             timestamp of last review)

- [ ] Generate migration



## Permissions & visibility rules

- [ ] Teachers:

&nbsp; - [ ] Can review (PATCH) submissions for exercises in their assigned courses

&nbsp; - [ ] Can set `teacher_comment`, `teacher_is_correct`

&nbsp; - [ ] `reviewed_by` and `reviewed_at` set automatically by the view

- [ ] Admins:

&nbsp; - [ ] Can review any submission in their tenant

- [ ] Students:

&nbsp; - [ ] Can read `teacher_comment` and `teacher_is_correct` on their own submissions

&nbsp; - [ ] Cannot write any review fields



## API endpoints

- [ ] PATCH /api/v1/submissions/{id}/review/

&nbsp; - Body: `{ "teacher_comment": "...", "teacher_is_correct": true|false|null }`

&nbsp; - Teacher: only submissions in their assigned courses

&nbsp; - Admin: any submission in tenant

&nbsp; - Student: 403

&nbsp; - Sets `reviewed_by` = request.user, `reviewed_at` = now()

&nbsp; - Returns updated submission (teacher serializer view)

- [ ] Update GET /api/v1/submissions/{id} student response

&nbsp; - Include `teacher_comment` and `teacher_is_correct` (read-only)

&nbsp; - Students already use `SubmissionSerializer` — add these two fields



## Serializers

- [ ] Add `teacher_comment`, `teacher_is_correct`, `reviewed_at` to
      `SubmissionSerializer` (students see comment + verdict, not reviewed_by)

- [ ] Add `teacher_comment`, `teacher_is_correct`, `reviewed_by`,
      `reviewed_at` to `SubmissionTeacherSerializer`

- [ ] New `SubmissionReviewSerializer` (write):

&nbsp; - [ ] Fields: `teacher_comment`, `teacher_is_correct`

&nbsp; - [ ] Both optional (partial review allowed)



## Tests

- [ ] Teacher (assigned) can review a submission in their course

- [ ] Teacher (assigned) can leave comment only (no verdict) — partial update

- [ ] Teacher (unassigned) cannot review submission in another course (403)

- [ ] Admin can review any submission in tenant

- [ ] Student cannot PATCH review endpoint (403)

- [ ] Reviewed fields appear in student's GET /submissions/{id} response

- [ ] `reviewed_by` and `reviewed_at` are set automatically on review

- [ ] Reviewing twice updates `reviewed_at` and `reviewed_by`

- [ ] Cross-tenant review forbidden (404)



## Acceptance criteria

- Teachers can leave a manual grade and comment on any submission in their course

- Students can see the teacher comment and verdict on their own submission

- `reviewed_by` and `reviewed_at` are always set server-side — clients cannot forge them

- Existing AI messages and `is_correct` (MCQ auto-grade) are unaffected

- All endpoints remain tenant-safe

- Tests pass: `docker compose run backend python manage.py test`
