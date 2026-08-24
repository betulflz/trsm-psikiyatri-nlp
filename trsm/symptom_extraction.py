import re

SPLIT_PATTERN = re.compile(r"[.,;\n]|->|\s-\s")


def split_into_phrases(text, min_length=6):
    if not text:
        return []
    parts = SPLIT_PATTERN.split(text)
    phrases = [p.strip() for p in parts]
    return [p for p in phrases if len(p) >= min_length]
