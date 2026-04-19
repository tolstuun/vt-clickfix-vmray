import pytest

from app.services.url_extractor import extract_urls, url_hash, _refang, _normalize, parse_source_from_comment


def test_extract_basic_hxxp():
    results = extract_urls("Download from hxxp://evil[.]com/payload.exe here")
    assert len(results) == 1
    original, normalized = results[0]
    assert original == "hxxp://evil[.]com/payload.exe"
    assert normalized == "http://evil.com/payload.exe"


def test_extract_basic_hxxps():
    results = extract_urls("Visit hxxps://example[.]com/path?q=1")
    assert len(results) == 1
    _, normalized = results[0]
    assert normalized == "https://example.com/path?q=1"


def test_extract_bracket_dot():
    results = extract_urls("hxxp://malware[dot]io/stage1")
    assert len(results) == 1
    _, normalized = results[0]
    assert normalized == "http://malware.io/stage1"


def test_extract_multiple_urls():
    text = "hxxp://bad[.]com/a and hxxps://also[.]bad[.]com/b"
    results = extract_urls(text)
    assert len(results) == 2
    normalized = [n for _, n in results]
    assert "http://bad.com/a" in normalized
    assert "https://also.bad.com/b" in normalized


def test_deduplication():
    text = "hxxp://dup[.]com/x and hxxp://dup[.]com/x"
    results = extract_urls(text)
    assert len(results) == 1


def test_no_defanged_urls():
    results = extract_urls("nothing to see here https://normal.com/path")
    assert results == []


def test_trailing_punctuation_stripped():
    results = extract_urls("see hxxp://site[.]com/path.")
    _, normalized = results[0]
    assert normalized == "http://site.com/path"


def test_url_hash_is_sha256():
    import hashlib
    h = url_hash("https://example.com")
    assert h == hashlib.sha256(b"https://example.com").hexdigest()
    assert len(h) == 64


def test_url_hash_deterministic():
    assert url_hash("https://x.com/a") == url_hash("https://x.com/a")


def test_refang_hxxp():
    assert _refang("hxxp://x.com") == "http://x.com"


def test_refang_hxxps():
    assert _refang("hxxps://x.com") == "https://x.com"


def test_refang_bracket_dot():
    assert _refang("hxxp://x[.]com") == "http://x.com"


def test_refang_dot_notation():
    assert _refang("hxxp://x[dot]com") == "http://x.com"


def test_normalize_lowercases_host():
    assert _normalize("http://EVIL.COM/Path") == "http://evil.com/Path"


def test_normalize_strips_trailing_comma():
    assert _normalize("http://evil.com/x,") == "http://evil.com/x"


# parse_source_from_comment

def test_parse_source_exact_phrase():
    assert parse_source_from_comment('IOC found on "ThreatFox"') == "ThreatFox"


def test_parse_source_plural():
    assert parse_source_from_comment('IOCs found on "URLhaus"') == "URLhaus"


def test_parse_source_case_insensitive():
    assert parse_source_from_comment('ioc found on "MalwareBazaar"') == "MalwareBazaar"


def test_parse_source_embedded_in_text():
    text = "Some context.\nIOC found on \"ThreatFox\"\nhxxp://evil[.]com/x"
    assert parse_source_from_comment(text) == "ThreatFox"


def test_parse_source_no_phrase_returns_none():
    assert parse_source_from_comment("hxxp://evil[.]com/x no source phrase here") is None


def test_parse_source_empty_text():
    assert parse_source_from_comment("") is None


def test_parse_source_plain_no_quotes():
    assert parse_source_from_comment("IOC found on ThreatFox") == "ThreatFox"


def test_parse_source_plain_newline_terminated():
    assert parse_source_from_comment("IOC found on ThreatFox\nmore text") == "ThreatFox"


def test_parse_source_plain_trailing_punctuation_stripped():
    assert parse_source_from_comment("IOC found on ThreatFox,") == "ThreatFox"


def test_parse_source_plain_embedded_in_multiline():
    text = "clickfix payload\nIOC found on URLhaus\nhxxp://evil[.]com/x"
    assert parse_source_from_comment(text) == "URLhaus"
