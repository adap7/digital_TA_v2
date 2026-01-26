\## Goal

Introduce tenant (university/program) model and associate users with a tenant.



\## Tasks

\- \[ ] Create Tenant model

&nbsp; - \[ ] Name

&nbsp; - \[ ] Unique identifier (slug or code)

&nbsp; - \[ ] Created timestamp

\- \[ ] Associate User with Tenant

&nbsp; - \[ ] Add tenant foreign key to User

\- \[ ] Register Tenant in Django admin

\- \[ ] Update User admin to display tenant

\- \[ ] Create tenant via admin

\- \[ ] Assign users to tenant

\- \[ ] Run migrations cleanly



\## Acceptance criteria

\- Tenant model exists

\- Every user belongs to exactly one tenant

\- Admin can create and manage tenants

\- Admin can assign users to tenants

\- No cross-tenant ambiguity in the data model



