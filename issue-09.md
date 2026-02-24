## Goal

Allow students to submit answers to published exercises and receive immediate AI-generated feedback via the Claude API. Students can continue a multi-turn conversation with the AI tutor about the exercise. Multiple attempts are supported.



## Scope

- Submission model (one per attempt, resubmission allowed)

- AI evaluation on submit (Claude API call, immediate feedback)

- Multi-turn AI chat per submission

- MCQ auto-grading (answer compared to answer\_key)

- Student access to own submissions only

- Teacher/admin read access to all submissions in their courses

- Core API endpoints

- Tests for role + tenant isolation



## Data model

- [ ] Create `Submission` model

&nbsp; - [ ] exercise (FK → Exercise, CASCADE)

&nbsp; - [ ] student (FK → User, CASCADE)

&nbsp; - [ ] answer (JSONField — `{"text": "..."}` / `{"choice": "B"}` / `{"latex": "..."}`)

&nbsp; - [ ] attempt\_number (PositiveSmallIntegerField, auto-set)

&nbsp; - [ ] is\_correct (BooleanField, nullable — auto-set for MCQ, null for free-text/latex)

&nbsp; - [ ] submitted\_at (DateTimeField, auto\_now\_add)

- [ ] Create `SubmissionMessage` model

&nbsp; - [ ] submission (FK → Submission, CASCADE)

&nbsp; - [ ] role (CharField — `student` / `assistant`)

&nbsp; - [ ] content (TextField)

&nbsp; - [ ] created\_at (DateTimeField, auto\_now\_add)

- [ ] Enforce tenant safety via student.tenant == exercise.course.tenant

- [ ] No unique\_together on (exercise, student) — resubmission allowed



## AI integration

- [ ] Create `courses/ai.py` service module

&nbsp; - [ ] `evaluate_submission(exercise, student_answer)` — evaluates answer, returns feedback text

&nbsp; - [ ] `get_followup_response(exercise, messages)` — continues conversation given full history

- [ ] Use `claude-sonnet-4-6` via Anthropic SDK, Use GPT via OpenAI and Use DeepSeek

- [ ] Pass exercise prompt, type, difficulty, and answer\_key to LLM (answer\_key never returned to student)

- [ ] If LLM call fails, return 503 — do not save a broken submission

- [ ] Add `anthropic` to requirements.txt



## Permissions & visibility rules

- [ ] Students:

&nbsp; - [ ] Can submit to PUBLISHED exercises in enrolled courses only

&nbsp; - [ ] Can view own submissions and messages only

&nbsp; - [ ] Can send follow-up messages on own submissions

&nbsp; - [ ] Cannot see other students' submissions

- [ ] Teachers:

&nbsp; - [ ] Can list all submissions for exercises in their assigned courses (read-only)

- [ ] Admins:

&nbsp; - [ ] Can view all submissions within tenant (read-only)



## API endpoints

- [ ] POST /api/v1/exercises/{id}/submissions

&nbsp; - Student submits answer

&nbsp; - Triggers LLM evaluation

&nbsp; - Returns submission + first AI message

- [ ] GET /api/v1/exercises/{id}/submissions

&nbsp; - Student: own submissions only

&nbsp; - Teacher/Admin: all submissions for that exercise

- [ ] GET /api/v1/submissions/{id}

&nbsp; - Returns submission with nested messages

&nbsp; - Student: own only; Teacher/Admin: any in tenant

- [ ] POST /api/v1/submissions/{id}/messages

&nbsp; - Student sends follow-up question

&nbsp; - AI responds using full conversation history

&nbsp; - Returns new AI message



## Tests

- [ ] Student can submit to published exercise in enrolled course

- [ ] Student cannot submit to draft exercise

- [ ] Student cannot submit to exercise in non-enrolled course

- [ ] Student can resubmit (attempt\_number increments)

- [ ] MCQ submission sets is\_correct automatically

- [ ] Student cannot see other students' submissions

- [ ] Student can send follow-up message and receive AI reply

- [ ] Teacher can list all submissions for their course exercise

- [ ] Teacher cannot access submissions in unassigned course

- [ ] Admin can view any submission in tenant

- [ ] Cross-tenant submission access forbidden



## Acceptance criteria

- Student submits an answer and receives immediate AI feedback in the response

- MCQ answers are auto-checked (is\_correct set) in addition to LLM feedback

- Student can continue a multi-turn conversation with the AI about the exercise

- Multiple attempts are allowed per exercise

- Students only see their own submissions

- answer\_key never leaks to students at any endpoint

- All endpoints are tenant-safe

- Tests pass in Docker: `docker compose run backend python manage.py test`
