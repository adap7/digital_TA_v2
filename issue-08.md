\## Goal

Implement Exercises with a teacher review/publish workflow, and enforce student visibility rules.



Exercises are the core unit students will practice. Teachers/admins can create and review exercises, but students can only access published exercises in their enrolled courses.



\## Scope

\- Exercise model + publishing workflow

\- Topic assignment (exercise belongs to a course; optionally belongs to a topic)

\- Student read-only access to published exercises

\- Teacher/admin create/update/review/publish

\- Core API endpoints

\- Tests for role + tenant isolation



\## Data model

\- \[ ] Create Exercise model

&nbsp; - \[ ] course (FK)

&nbsp; - \[ ] topic (FK, nullable initially to allow course-level exercises)

&nbsp; - \[ ] title (optional) or short\_label

&nbsp; - \[ ] type (MCQ / FREE\_TEXT / LATEX)

&nbsp; - \[ ] prompt (text)

&nbsp; - \[ ] choices (JSON, nullable; for MCQ)

&nbsp; - \[ ] answer\_key / grading\_spec (JSON or text; teacher/admin only; never returned to students)

&nbsp; - \[ ] difficulty (int or enum)

&nbsp; - \[ ] order\_index (int, per topic or per course feed)

&nbsp; - \[ ] status (DRAFT / IN\_REVIEW / PUBLISHED)

&nbsp; - \[ ] created\_by (FK User)

&nbsp; - \[ ] reviewed\_by (FK User, nullable)

&nbsp; - \[ ] published\_at (datetime, nullable)

&nbsp; - \[ ] created\_at, updated\_at

\- \[ ] Enforce tenant safety via course.tenant



\## Permissions \& visibility rules

\- \[ ] Students:

&nbsp; - \[ ] Can list and retrieve only PUBLISHED exercises for their enrolled courses

&nbsp; - \[ ] Cannot see answer\_key/grading\_spec

\- \[ ] Teachers:

&nbsp; - \[ ] Can create/edit exercises only in their assigned courses

&nbsp; - \[ ] Can move exercises to IN\_REVIEW and PUBLISHED

&nbsp; - \[ ] Must be able to review before publish (explicit action)

\- \[ ] Admins:

&nbsp; - \[ ] Full access within tenant



\## API endpoints

\- \[ ] GET /api/v1/courses/{course\_id}/exercises

&nbsp; - Student: only published

&nbsp; - Teacher/Admin: all (including drafts)

\- \[ ] POST /api/v1/courses/{course\_id}/exercises (Teacher/Admin)

\- \[ ] GET /api/v1/exercises/{id}

&nbsp; - Student: published only

&nbsp; - Teacher/Admin: any

\- \[ ] PATCH /api/v1/exercises/{id} (Teacher/Admin)

\- \[ ] POST /api/v1/exercises/{id}/submit-for-review (Teacher/Admin)

\- \[ ] POST /api/v1/exercises/{id}/publish (Teacher/Admin)

\- \[ ] (Optional) POST /api/v1/exercises/{id}/unpublish (Teacher/Admin)



\## Tests

\- \[ ] Student cannot view draft exercises

\- \[ ] Student cannot access exercises from non-enrolled course

\- \[ ] Teacher can create exercise in assigned course

\- \[ ] Teacher cannot create exercise in unassigned course

\- \[ ] Admin can access all tenant exercises

\- \[ ] Cross-tenant exercise access forbidden

\- \[ ] Publishing workflow changes status correctly

\- \[ ] Student never receives answer\_key/grading\_spec fields



\## Acceptance criteria

\- Exercise CRUD + workflow endpoints exist and are tenant-safe

\- Students only see published exercises for their courses

\- Teachers must explicitly publish exercises (review step supported)

\- Sensitive fields never leak to students

\- Tests pass in Docker: `docker compose run backend python manage.py test`



