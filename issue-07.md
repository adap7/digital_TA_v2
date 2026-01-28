\# Issue-07 — Course Topics \& Publishing Workflow



\## Goal



Introduce topics as the structural layer inside courses and enforce a draft vs published workflow, so teachers control what students see.



This issue establishes the foundation for structured learning paths and safe content release.



\## Context



Courses must be structured into ordered topics (e.g. “Limits”, “Derivatives”, “Integrals”).



\- Teachers and admins manage topics

\- Students only see published topics

\- Topics will later contain exercises (Issue-08)



\## Scope (In scope)



\- Topic model

\- Topic ordering

\- Publishing workflow

\- Role-based visibility

\- API endpoints

\- Tests



\## Tasks



\### Data model

\- \[ ] Create `Topic` model

&nbsp; - \[ ] Belongs to a `Course`

&nbsp; - \[ ] `title`

&nbsp; - \[ ] `order\_index` (integer, used for ordering)

&nbsp; - \[ ] `is\_published` (boolean, default = false)

&nbsp; - \[ ] `created\_at`

\- \[ ] Enforce unique ordering per course (course + order\_index)



\### Permissions \& visibility

\- \[ ] Teachers can:

&nbsp; - \[ ] Create topics for assigned courses

&nbsp; - \[ ] Edit topics

&nbsp; - \[ ] Publish / unpublish topics

\- \[ ] Admins can:

&nbsp; - \[ ] Manage topics for any course in tenant

\- \[ ] Students can:

&nbsp; - \[ ] Only see topics where `is\_published = true`

&nbsp; - \[ ] Only see topics in enrolled courses



\### API endpoints

\- \[ ] `GET /api/v1/courses/{id}/topics`

&nbsp; - \[ ] Teacher/Admin: all topics

&nbsp; - \[ ] Student: only published topics

\- \[ ] `POST /api/v1/courses/{id}/topics`

&nbsp; - \[ ] Teacher/Admin only

\- \[ ] `PATCH /api/v1/topics/{id}`

&nbsp; - \[ ] Update title, order, publish state

\- \[ ] Enforce tenant + course membership checks on all endpoints



\### Ordering logic

\- \[ ] Topics returned ordered by `order\_index`

\- \[ ] Prevent duplicate order indices within the same course



\### Tests

\- \[ ] Teacher can create topics

\- \[ ] Student cannot create topics

\- \[ ] Student sees only published topics

\- \[ ] Teacher sees unpublished topics

\- \[ ] Cross-tenant access forbidden

\- \[ ] Topic ordering respected



\## Acceptance criteria

\- Topics exist as first-class entities

\- Topic visibility is role-aware

\- Students never see unpublished topics

\- Teachers control publishing

\- All endpoints are tenant-safe

\- All tests pass



\## Out of scope (explicitly excluded)

\- Exercises inside topics (Issue-08)

\- AI-generated topics

\- Frontend UI

\- Reordering via drag-and-drop



\## Why this matters



This issue creates:

\- A clear learning structure

\- Safe teacher-controlled content release

\- The backbone for exercises, analytics, and AI tutoring

