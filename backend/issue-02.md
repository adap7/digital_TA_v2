## Goal

Set up Django backend foundation using Docker with a clean project structure and dependencies.

## Tasks

- [x] Backend runs inside Docker (no local virtualenv)
- [X] Create Django project
- [X] freeze requirements.txt
- [X] Create core Django apps
  - [X] users
  - [X] courses
- [ ] Install backend dependencies
  - [ ] Django
  - [ ] Django REST Framework
- [ ] Freeze dependencies into requirements.txt
- [ ] Run initial migrations
- [ ] Verify Django development server runs in Docker

## Acceptance criteria

- Django server starts without errors inside Docker
- Admin panel loads
- Project structure supports future auth & multi-tenancy
- requirements.txt exists and is correct