"""Dependency-free text helpers shared by the SEO engines."""
import re

STOPWORDS = set("""a an the and or but of in on at to for from by with about as is are was were be been it its this that these those
your you our we they their i me my do does did can could should would will how what why when where which who whom vs versus
near best top""".split())
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def stem(w: str) -> str:
    for suf in ("ing", "es", "s", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokens(text: str, drop_stop: bool = True) -> list[str]:
    ws = _WORD.findall((text or "").lower())
    if drop_stop:
        ws = [w for w in ws if w not in STOPWORDS]
    return [stem(w) for w in ws]


def jaccard(a, b) -> float:
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def slugify(text: str, max_len: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rsplit("-", 1)[0] or s[:max_len]
    return s


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(n, 1)


def flesch_reading_ease(text: str):
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)
    if not sentences or len(words) < 30:
        return None
    syl = sum(syllables(w) for w in words)
    return round(206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (syl / len(words)), 1)
