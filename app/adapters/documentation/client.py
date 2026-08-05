import re
from collections.abc import Sequence
from html.parser import HTMLParser
from time import perf_counter
from typing import Final
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from app.core.logging import get_logger
from app.domain.documentation.exceptions import DocumentationUnavailableError
from app.domain.documentation.ports import DocumentationRepository
from app.models.documentation.models import DocumentationPage

logger = get_logger(__name__)

_USER_AGENT: Final = "NRPilot/0.1 documentation retrieval"
_MAX_EXCERPT_LENGTH: Final = 2_000


class NRPDocumentationClient(DocumentationRepository):
    """Read-only retrieval client for the official NRP documentation site."""

    def __init__(
        self,
        documentation_url: str,
        timeout_seconds: float,
        max_results: int,
    ) -> None:
        self._documentation_url = _canonical_url(documentation_url)
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results
        self._documentation_origin = _origin(self._documentation_url)
        self._documentation_path = urlsplit(self._documentation_url).path.rstrip("/")

    def search(self, query: str) -> Sequence[DocumentationPage]:
        started_at = perf_counter()
        logger.debug(
            "nrp_documentation_search_started",
            query_length=len(query),
            max_results=self._max_results,
        )
        links = self._documentation_links()
        prioritized_links = _rank_links(
            links,
            query,
            min(len(links), self._max_results * 5),
        )
        logger.debug(
            "nrp_documentation_links_ranked",
            query_term_count=len(_query_terms(query)),
            prioritized_links=prioritized_links,
        )

        scored_pages: list[tuple[int, str, str, str]] = []
        for title, url in prioritized_links:
            page_title, content, headings = self._get_page(url)
            if not content:
                continue
            score = _page_score(query, title, url, page_title, content, headings)
            scored_pages.append((score, page_title or title, url, content))

        scored_pages.sort(key=lambda page: (-page[0], page[1]))
        logger.debug(
            "nrp_documentation_pages_scored",
            scored_pages_count=len(scored_pages),
            scored_pages=scored_pages,
        )
        pages: list[DocumentationPage] = []
        for _, title, url, content in scored_pages[: self._max_results]:
            pages.append(
                DocumentationPage(
                    title=title,
                    url=url,
                    excerpt=content[:_MAX_EXCERPT_LENGTH],
                )
            )

        logger.debug(
            "nrp_documentation_search_completed",
            result_count=len(pages),
            duration_seconds=perf_counter() - started_at,
        )
        return pages

    def _documentation_links(self) -> list[tuple[str, str]]:
        _, html = self._fetch(self._documentation_url)
        parser = _PageParser()
        parser.feed(html)

        links = [(parser.title or "NRP documentation", self._documentation_url)]
        for title, href in parser.links:
            url = _canonical_url(urljoin(self._documentation_url, href))
            if self._is_documentation_url(url):
                links.append((title, url))
        unique_links = list(dict.fromkeys(links))
        logger.debug(
            "nrp_documentation_links_discovered",
            documentation_url=self._documentation_url,
            link_count=len(unique_links),
        )
        return unique_links

    def _get_page(self, url: str) -> tuple[str, str, list[str]]:
        _, html = self._fetch(url)
        parser = _PageParser()
        parser.feed(html)
        logger.debug(
            "nrp_documentation_page_parsed",
            url=url,
            title=parser.title,
            content_length=len(parser.content),
        )
        return parser.title, parser.content, parser.headings

    def _fetch(self, url: str) -> tuple[str, str]:
        request = Request(url, headers={"User-Agent": _USER_AGENT})
        started_at = perf_counter()
        logger.debug("nrp_documentation_fetch_started", url=url)
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read()
                final_url = response.geturl()
                logger.debug(
                    "nrp_documentation_fetch_completed",
                    url=url,
                    final_url=final_url,
                    status_code=response.getcode(),
                    response_bytes=len(body),
                    duration_seconds=perf_counter() - started_at,
                )
                return final_url, body.decode(charset, errors="replace")
        except OSError as exc:
            logger.warning("nrp_documentation_request_failed", url=url)
            raise DocumentationUnavailableError(
                "NRP documentation is currently unavailable"
            ) from exc

    def _is_documentation_url(self, url: str) -> bool:
        parts = urlsplit(url)
        return _origin(url) == self._documentation_origin and parts.path.startswith(
            self._documentation_path
        )


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.links: list[tuple[str, str]] = []
        self.content = ""
        self.headings: list[str] = []
        self._in_title = False
        self._in_main = False
        self._in_heading = False
        self._current_link: str | None = None
        self._current_link_text: list[str] = []
        self._current_heading_text: list[str] = []
        self._content_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "main":
            self._in_main = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._in_heading = True
            self._current_heading_text = []
        elif tag == "a" and (href := attributes.get("href")):
            self._current_link = href
            self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "main":
            self._in_main = False
            self.content = " ".join(self._content_parts).strip()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._in_heading = False
            heading_text = " ".join(self._current_heading_text).strip()
            if heading_text:
                self.headings.append(heading_text)
            self._current_heading_text = []
        elif tag == "a" and self._current_link:
            text = " ".join(self._current_link_text).strip()
            if text:
                self.links.append((text, self._current_link))
            self._current_link = None
            self._current_link_text = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title = f"{self.title} {text}".strip()
        if self._in_heading:
            self._current_heading_text.append(text)
        if self._current_link is not None:
            self._current_link_text.append(text)
        if self._in_main:
            self._content_parts.append(text)


def _rank_links(
    links: Sequence[tuple[str, str]], query: str, max_results: int
) -> list[tuple[str, str]]:
    ranked = sorted(
        links,
        key=lambda link: (
            -_link_score(link[0], link[1], query),
            link[0],
        ),
    )
    return ranked[:max_results]


def _link_score(title: str, url: str, query: str) -> int:
    terms = _query_terms(query)
    score = 0
    for term in terms:
        if term in title.lower():
            score += 3
        if term in url.lower():
            score += 1
    return score


def _page_score(
    query: str,
    link_title: str,
    url: str,
    page_title: str,
    content: str,
    headings: list[str],
) -> int:
    terms = _query_terms(query)
    if not terms:
        return 0

    def count_terms(text: str) -> int:
        lower = text.lower()
        return sum(lower.count(term) for term in terms)

    title_score = count_terms(page_title) * 4
    heading_score = sum(count_terms(h) for h in headings) * 7
    link_title_score = count_terms(link_title) * 2
    url_score = sum(term in url.lower() for term in terms) * 1
    body_score = count_terms(content) * 5

    phrase_bonus = 0
    normalized_query = _normalized_query(query)
    if normalized_query and normalized_query in content.lower():
        phrase_bonus = 18

    proximity_bonus = 0
    if len(terms) > 1 and phrase_bonus == 0:
        positions = [
            content.lower().find(term) for term in terms if term in content.lower()
        ]
        if len(positions) == len(terms) and max(positions) - min(positions) < 120:
            proximity_bonus = 8

    return (
        title_score
        + heading_score
        + link_title_score
        + url_score
        + body_score
        + phrase_bonus
        + proximity_bonus
    )


def _normalized_query(query: str) -> str:
    return " ".join(_query_terms(query))


def _query_terms(query: str) -> set[str]:
    return {
        term.lower() for term in re.findall(r"[A-Za-z0-9]+", query) if len(term) > 1
    }


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"
