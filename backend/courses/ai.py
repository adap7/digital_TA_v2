from django.conf import settings

MODEL_CLAUDE   = "claude-sonnet-4-6"
MODEL_GPT4O    = "gpt-4o"
MODEL_DEEPSEEK = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


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
        "## Your role as a tutor",
        "Your goal is to help the student *understand*, not to give them the answer.",
        "",
        "Rules you must always follow:",
        "1. NEVER state the correct answer or solution directly, even if the student asks for it outright.",
        "2. Instead, give targeted hints, ask guiding questions, and point out which part of their "
        "   reasoning is on the right track and which part needs rethinking.",
        "3. If the student's answer is wrong, explain *why* it is wrong conceptually — do not "
        "   simply say 'that's incorrect' without explanation.",
        "4. If the student has not attempted the problem yet, respond only with a clarifying "
        "   question or a small hint to get them started — do not solve any part of it for them.",
        "5. Only after the student has made a genuine attempt and shown their reasoning should "
        "   you give more detailed guidance.",
        "6. Never quote, paraphrase, or hint at the exact wording of the answer key.",
        "7. Be encouraging and concise.",
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


def _call_claude(system: str, messages: list) -> str:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL_CLAUDE,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _call_openai(model: str, system: str, messages: list, api_key: str, base_url: str = None) -> str:
    from openai import OpenAI
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    response = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "system", "content": system}] + messages,
    )
    return response.choices[0].message.content


def _dispatch(exercise, system: str, messages: list) -> str:
    model = exercise.course.ai_model
    if model == MODEL_CLAUDE:
        return _call_claude(system, messages)
    elif model == MODEL_GPT4O:
        return _call_openai(MODEL_GPT4O, system, messages, settings.OPENAI_API_KEY)
    elif model == MODEL_DEEPSEEK:
        return _call_openai(MODEL_DEEPSEEK, system, messages, settings.DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL)
    raise ValueError(f"Unknown AI model: {model}")


def evaluate_submission(exercise, student_answer: dict) -> str:
    """
    Evaluate a student's answer using the course's configured AI model.
    Returns feedback text.
    Raises on failure — the view should catch this and return 503.
    """
    system = _build_system_prompt(exercise)
    messages = [
        {
            "role": "user",
            "content": f"Here is my answer:\n\n{_format_answer(student_answer)}",
        }
    ]
    return _dispatch(exercise, system, messages)


def get_followup_response(exercise, messages) -> str:
    """
    Continue the AI chat for a submission given its full message history.
    `messages` is an ordered queryset/list of SubmissionMessage objects.
    Returns the AI's next response text.
    Raises on failure — the view should catch this and return 503.
    """
    system = _build_system_prompt(exercise)
    api_messages = [
        {
            "role": "user" if msg.role == "student" else "assistant",
            "content": msg.content,
        }
        for msg in messages
    ]
    return _dispatch(exercise, system, api_messages)
