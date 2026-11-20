"""
Tests for the linkstats module (no running server needed).

Run with:  pytest linkstats_src/tests -v   (from the module folder)
"""
import pytest

from ..service import agent_family, hash_ip, referer_host


@pytest.mark.parametrize(
    "ua,expected",
    [
        ("curl/8.5.0", "curl"),
        ("Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/120.0 Safari/537.36", "chrome"),
        ("Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/120.0 Safari/537.36 Edg/120.0", "edge"),
        ("Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15", "safari"),
        ("Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0", "firefox"),
        ("Googlebot/2.1 (+http://www.google.com/bot.html)", "bot"),
        ("WhatsApp/2.23", "other"),
        (None, "unknown"),
    ],
)
def test_agent_family(ua, expected):
    assert agent_family(ua) == expected


@pytest.mark.parametrize(
    "ref,expected",
    [
        (None, "direct"),
        ("", "direct"),
        ("https://www.twitter.com/some/post", "twitter.com"),
        ("http://newsletter.example.com/issue/4", "newsletter.example.com"),
        ("instagram.com", "instagram.com"),
    ],
)
def test_referer_host(ref, expected):
    assert referer_host(ref) == expected


def test_ip_hash_is_stable_salted_and_not_the_ip():
    h = hash_ip("10.0.0.1", "s1")
    assert h == hash_ip("10.0.0.1", "s1")
    assert h != hash_ip("10.0.0.1", "s2")
    assert "10.0.0.1" not in h and len(h) == 64
    assert hash_ip(None, "s1") is None


async def run_module_tests():
    """Entry point used by the ChaCC backbone (test_entry_point in module_meta.json)."""
    assert agent_family("curl/8") == "curl"
    assert referer_host("https://www.x.com/a") == "x.com"
