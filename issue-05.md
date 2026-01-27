\## Goal

Enforce tenant isolation and role-based access at the backend API level.



\## Tasks

\- \[ ] Add tenant-aware base queryset patterns

\- \[ ] Add request-level tenant context helper (user.tenant)

\- \[ ] Implement reusable DRF permission classes

&nbsp; - \[ ] IsStudent / IsTeacher / IsAdmin

&nbsp; - \[ ] TenantScopedAccess (object-level)

\- \[ ] Create a simple authenticated endpoint to validate enforcement

&nbsp; - \[ ] GET /api/v1/me (returns email, role, tenant)

\- \[ ] Add tests for tenant isolation and role checks



\## Acceptance criteria

\- Any request is implicitly scoped to the authenticated user's tenant

\- Cross-tenant access is impossible via API (403/404)

\- Role restrictions work (student/teacher/admin)

\- /api/v1/me works and returns tenant + role



