import hashlib
import re
from urllib.parse import urlparse, urlunparse

_DEFANGED_RE = re.compile(r"hxxps?://[^\s<>\"')]+", re.IGNORECASE)
_BRACKET_DOT_RE = re.compile(r"\[\.|\.|\]|\[dot\]", re.IGNORECASE)


def _refang(url: str) -> str:
    url = re.sub(r"hxxps://", "https://", url, flags=re.IGNORECASE)
    url = re.sub(r"hxxp://", "http://", url, flags=re.IGNORECASE)
    url = re.sub(r"\[dot\]", ".", url, flags=re.IGNORECASE)
    url = re.sub(r"\[\.\]", ".", url)
    return url


def _normalize(url: str) -> str:
    url = url.rstrip(".,;:)>\"']")
    parsed = urlparse(url)
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))


def url_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode()).hexdigest()


def extract_urls(text: str) -> list[tuple[str, str]]:
    """Extract defanged URLs from text.

    Returns list of (original_defanged, normalized_url) tuples, deduplicated by hash.
    """
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in _DEFANGED_RE.finditer(text):
        original = match.group(0)
        normalized = _normalize(_refang(original))
        h = url_hash(normalized)
        if h not in seen:
            seen.add(h)
            results.append((original, normalized))
    return results
