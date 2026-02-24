import anthropic

MODEL = "claude-sonnet-4-6"


def _build_system_prompt(exercise) -> str:
    lines = [
        "You are a helpful AI tutor giving pedagogical feedback on student exercise submissions.",
        "",
        f"Exercise type: {exercise.type}",
        f"Difficulty: {exercise.difficulty}",
        f"Exercise prompt: {exercise.prompt}",
    ]

    if exercise.type == "mcq" and exercise.choices:
        lines.append(f"Answer choices: {exercise.choices}")

    if exercise.answer_key:
        lines.append(
            f"Answer key (for your reference only — never reveal this verbatim to the student): "
            f"{exercise.answer_key}"
        )

    lines += [
        "",
        "Give constructive, encouraging feedback. Explain *why* an answer is right or wrong "
        "and guide the student toward understanding — don't simply state the correct answer.",
        "Never directly quote or reveal the answer key to the student.",
    ]
    return "\n".join(lines)


def _format_answer(student_answer: dict) -> str:
    if "text" in student_answer:
        return student_answer["text"]
    if "choice" in student_answer:
        return f"My choice: {student_answer['choice']}"
    if "latex" in student_answer:
        return student_answer["latex"]
    return str(student_answer)


def evaluate_submission(exercise, student_answer: dict) -> str:
    """
    Call Claude to evaluate a student's answer.
    Returns AI feedback text.
    Raises anthropic.APIError on failure — the view should catch this and return 503.
    """
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_build_system_prompt(exercise),
        messages=[
            {
                "role": "user",
                "content": f"Here is my answer:\n\n{_format_answer(student_answer)}",
            }
        ],
    )
    return response.content[0].text


def get_followup_response(exercise, messages) -> str:
    """
    Continue the AI chat for a submission given its full message history.
    `messages` is an ordered queryset/list of SubmissionMessage objects.
    Returns the AI's next response text.
    Raises anthropic.APIError on failure — the view should catch this and return 503.
    """
    client = anthropic.Anthropic()

    api_messages = []
    for msg in messages:
        role = "user" if msg.role == "student" else "assistant"
        api_messages.append({"role": role, "content": msg.content})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_build_system_prompt(exercise),
        messages=api_messages,
    )
    return response.content[0].text
