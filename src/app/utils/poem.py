from django.utils import timezone

_TRAILING_PUNCTUATION = " .,!:?;…—-"


def normalize_content(content: str) -> str:
    lines = content.split("\n")
    lines = [line.rstrip() for line in lines]

    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def derive_title(content: str, fallback_title: str | None) -> str:
    if fallback_title:
        return fallback_title

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        cleaned = stripped.rstrip(_TRAILING_PUNCTUATION)
        if not cleaned:
            continue

        if len(cleaned) > 100:
            cleaned = cleaned[:100]

        return f'"{cleaned}..."'

    return ""


def derive_comment(comment: str | None) -> str:
    if comment:
        return comment

    return timezone.localdate().strftime("%d.%m.%Y")
