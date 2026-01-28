\## Goal

Expose a tenant-scoped course listing API that returns only courses visible to the authenticated user.



\## API

GET /api/v1/courses/



\## Tasks

\- \[ ] Define Course ↔ Tenant relationship

\- \[ ] Define enrollment / assignment model

\- \[ ] Implement tenant-scoped queryset

\- \[ ] Apply role-based filtering:

&nbsp; - Student: enrolled courses only

&nbsp; - Teacher: assigned courses only

&nbsp; - Admin: all tenant courses

\- \[ ] Create CourseList serializer (minimal fields)

\- \[ ] Wire endpoint in api/urls.py



\## Tests

\- \[ ] Student sees only their enrolled courses

\- \[ ] Teacher sees only assigned courses

\- \[ ] Admin sees all tenant courses

\- \[ ] Cross-tenant access impossible



\## Acceptance criteria

\- GET /api/v1/courses/ returns 200 for authenticated users

\- No cross-tenant data leakage

\- Role-based filtering works

\- Tests pass in Docker

