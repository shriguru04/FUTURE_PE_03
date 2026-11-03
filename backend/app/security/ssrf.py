"""SSRF-safe, size-limited, robots-aware page fetcher. Content returned is UNTRUSTED data."""
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ..core.config import get_settings
from ..core.errors import AppError

UA = "AISEOBlogBot/1.0 (+contact: site admin)"


def validate_public_url(url: str) -> str:
    u = urlparse(url.strip())
    if u.scheme not in ("http", "https") or not u.hostname:
        raise AppError(422, "invalid_url", "Only http(s) URLs with a hostname are allowed")
    if u.username or u.password:
        raise AppError(422, "invalid_url", "Credentials in URLs are not allowed")
    if u.port not in (None, 80, 443):
        raise AppError(422, "invalid_url", "Only ports 80 and 443 are allowed")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise AppError(422, "unresolvable_host", "Host could not be resolved")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise AppError(422, "blocked_destination", "URL resolves to a non-public address")
    return u.geturl()


def allowed_by_robots(url: str) -> bool:
    u = urlparse(url)
    robots = f"{u.scheme}://{u.netloc}/robots.txt"
    try:
        validate_public_url(robots)
        r = httpx.get(robots, timeout=get_settings().fetch_timeout, headers={"User-Agent": UA}, follow_redirects=False)
        if r.status_code >= 400:
            return True
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, url)
    except Exception:
        return True


def fetch_html(url: str, max_redirects: int = 3) -> str:
    s = get_settings()
    cur = validate_public_url(url)
    if not allowed_by_robots(cur):
        raise AppError(403, "robots_disallowed", "robots.txt does not allow fetching this page")
    with httpx.Client(timeout=s.fetch_timeout, headers={"User-Agent": UA}, follow_redirects=False) as c:
        for _ in range(max_redirects + 1):
            with c.stream("GET", cur) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    cur = validate_public_url(urljoin(cur, r.headers["location"]))  # re-validate each hop
                    continue
                if r.status_code >= 400:
                    raise AppError(502, "fetch_failed", f"Website returned HTTP {r.status_code}")
                if "html" not in r.headers.get("content-type", "").lower():
                    raise AppError(422, "not_html", "URL did not return an HTML page")
                buf = bytearray()
                for chunk in r.iter_bytes():
                    buf += chunk
                    if len(buf) > s.fetch_max_bytes:
                        break
                return bytes(buf[: s.fetch_max_bytes]).decode(r.encoding or "utf-8", errors="replace")
    raise AppError(502, "too_many_redirects", "Too many redirects")


class _P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title, self.meta, self.h, self.text, self._in, self.skip = "", "", [], [], None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "template"):
            self.skip += 1
        if tag == "title":
            self._in = "title"
        elif tag in ("h1", "h2"):
            self._in = "h"
        elif tag == "meta" and (a.get("name") or "").lower() == "description":
            self.meta = (a.get("content") or "")[:300]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self.skip:
            self.skip -= 1
        if tag in ("title", "h1", "h2"):
            self._in = None

    def handle_data(self, d):
        if self.skip:
            return
        d = d.strip()
        if not d:
            return
        if self._in == "title":
            self.title += d
        elif self._in == "h":
            self.h.append(d)
        self.text.append(d)


def parse_page(html: str) -> dict:
    p = _P()
    p.feed(html)
    return {"title": p.title[:300], "meta_description": p.meta, "headings": p.h[:15],
            "text_excerpt": " ".join(p.text)[:1500]}
