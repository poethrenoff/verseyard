from django.conf import settings

_SCORE_KEYS = ("freshness", "emotional_density", "voice", "completeness")

_SYSTEM_PROMPT = (
    "Ты — строгий литературный критик. Оцени стихотворение по четырём шкалам от 0 до 10 "
    "(дробные значения округляй до целого). Верни ТОЛЬКО JSON без markdown-разметки:\n"
    "{\n"
    '  "freshness": int,          // свежесть образа: насколько небанальны, новы метафоры и образы\n'
    '  "emotional_density": int,  // эмоциональная плотность: насыщенность и подлинность чувства\n'
    '  "voice": int,              // голос: узнаваемость авторской интонации, своеобразие\n'
    '  "completeness": int,       // завершённость: цельность, законченность формы и мысли\n'
    '  "comment": string          // короткий (1-3 предложения) комментарий на русском\n'
    "}\n"
    "Будь честным, не завышай оценки."
)

_USER_PROMPT = "Стихотворение для оценки:\n\n{poem}"


def assess(content: str) -> dict:
    if not settings.LLM_API_URL or not settings.LLM_MODEL_NAME:
        raise RuntimeError("LLM not configured: set LLM_API_URL and LLM_MODEL_NAME")

    from openai import OpenAI

    client = OpenAI(base_url=settings.LLM_API_URL, api_key=settings.LLM_API_KEY or "not-set")

    response = client.chat.completions.create(
        model=settings.LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_PROMPT.format(poem=content)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("Empty LLM response")

    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON from LLM: {raw!r}") from error

    scores: dict[str, int] = {}
    for key in _SCORE_KEYS:
        value = data.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(f"Missing or invalid score for {key}: {value!r}")
        scores[key] = int(max(0, min(10, round(float(value)))))

    comment = data.get("comment")
    scores["comment"] = comment if isinstance(comment, str) else ""

    return scores
