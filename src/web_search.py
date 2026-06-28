"""DuckDuckGo HTML-scrape web search.

Used by src/tasks/decide_next.py when the agent requests web search in its
first call. Defensive: any failure returns an empty list. No exception ever
propagates to the caller.

stdlib HTML parsing via html.parser keeps the dependency set unchanged
(httpx, pydantic, pyyaml, python-dotenv).
"""

from __future__ import annotations

import re
import urllib.parse
from html import unescape
from html.parser import HTMLParser

import httpx


DUCKDUCKGO_HTML_ENDPOINT = "https://html.duckduckgo.com/html/"
USER_AGENT = "agent-001/0.1 (https://github.com/Massideation/agent-grows-up)"
TIMEOUT_S = 12.0

_SNIPPET_MAX_CHARS = 250
_RESULT_LIMIT_CEILING = 10
_WHITESPACE_RE = re.compile(r"\s+")


class _DuckDuckGoResultParser(HTMLParser):
    """Collect result blocks from a DuckDuckGo HTML search response.

    Walks the document and tracks three nested states: inside a result block
    (div with a class containing "result"), inside the title anchor
    (a.result__a), and inside a snippet container (a.result__snippet or
    div.result__snippet). Text accumulated inside each state is attached to
    the current result.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict] = []
        self._current: dict | None = None
        self._result_depth = 0
        self._in_title = False
        self._title_depth = 0
        self._in_snippet = False
        self._snippet_depth = 0
        self._title_buf: list[str] = []
        self._snippet_buf: list[str] = []

    def _classes(self, attrs: list[tuple[str, str | None]]) -> set[str]:
        for name, value in attrs:
            if name == "class" and value:
                return set(value.split())
        return set()

    def _href(self, attrs: list[tuple[str, str | None]]) -> str:
        for name, value in attrs:
            if name == "href" and value:
                return value
        return ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = self._classes(attrs)

        if tag == "div" and "result" in classes and self._current is None:
            self._current = {"title": "", "url": "", "snippet": ""}
            self._result_depth = 1
            return

        if self._current is None:
            return

        # Track nesting depth so we know when the result block actually ends.
        if tag == "div":
            self._result_depth += 1

        if tag == "a" and "result__a" in classes and not self._in_title:
            self._in_title = True
            self._title_depth = 1
            self._title_buf = []
            href = self._href(attrs)
            if href and not self._current["url"]:
                self._current["url"] = _resolve_url(href)
            return

        if self._in_title and tag == "a":
            self._title_depth += 1

        if (
            tag in ("a", "div")
            and "result__snippet" in classes
            and not self._in_snippet
        ):
            self._in_snippet = True
            self._snippet_depth = 1
            self._snippet_buf = []
            return

        if self._in_snippet and tag in ("a", "div"):
            self._snippet_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return

        if self._in_title and tag == "a":
            self._title_depth -= 1
            if self._title_depth <= 0:
                self._in_title = False
                title_text = _clean_text("".join(self._title_buf))
                if title_text and not self._current["title"]:
                    self._current["title"] = title_text
                self._title_buf = []
                return

        if self._in_snippet and tag in ("a", "div"):
            self._snippet_depth -= 1
            if self._snippet_depth <= 0:
                self._in_snippet = False
                snippet_text = _clean_text("".join(self._snippet_buf))
                if snippet_text and not self._current["snippet"]:
                    self._current["snippet"] = _truncate(snippet_text, _SNIPPET_MAX_CHARS)
                self._snippet_buf = []
                return

        if tag == "div":
            self._result_depth -= 1
            if self._result_depth <= 0:
                self._finalize_current()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_buf.append(data)
        elif self._in_snippet:
            self._snippet_buf.append(data)

    def _finalize_current(self) -> None:
        if self._current is None:
            return
        result = self._current
        self._current = None
        self._result_depth = 0
        self._in_title = False
        self._title_depth = 0
        self._in_snippet = False
        self._snippet_depth = 0
        self._title_buf = []
        self._snippet_buf = []
        if not result["title"] and not result["url"]:
            return
        self.results.append(result)


def _clean_text(raw: str) -> str:
    """Unescape HTML entities, collapse whitespace, strip."""
    if not raw:
        return ""
    text = unescape(raw)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _resolve_url(href: str) -> str:
    """Decode DuckDuckGo's redirect wrapper if present, else return href."""
    if not href:
        return ""
    candidate = href
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    try:
        parsed = urllib.parse.urlparse(candidate)
    except ValueError:
        return href
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        query = urllib.parse.parse_qs(parsed.query)
        uddg = query.get("uddg")
        if uddg and uddg[0]:
            try:
                return urllib.parse.unquote(uddg[0])
            except (TypeError, ValueError):
                return href
    return candidate


def search(query: str, limit: int = 5) -> list[dict]:
    """Search DuckDuckGo's HTML endpoint and return up to `limit` results.

    Each result is a dict with keys: title (str), url (str), snippet (str).
    Any failure (network error, unexpected HTML shape, non-200 status, empty
    query) returns []. This function never raises.
    """
    if not isinstance(query, str):
        return []
    cleaned = query.strip()
    if not cleaned:
        return []

    try:
        clamped = int(limit)
    except (TypeError, ValueError):
        clamped = 5
    if clamped < 1:
        clamped = 1
    if clamped > _RESULT_LIMIT_CEILING:
        clamped = _RESULT_LIMIT_CEILING

    try:
        response = httpx.get(
            DUCKDUCKGO_HTML_ENDPOINT,
            params={"q": cleaned},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_S,
            follow_redirects=True,
        )
    except httpx.HTTPError:
        return []
    except Exception:
        return []

    if response.status_code != 200:
        return []

    try:
        body = response.text
    except Exception:
        return []

    parser = _DuckDuckGoResultParser()
    try:
        parser.feed(body)
        parser.close()
    except Exception:
        return []

    return parser.results[:clamped]
