from html.parser import HTMLParser

from app.scanning.context import LinkObservation


class _AnchorExtractor(HTMLParser):
    """Collects every <a href="..."> tag's href and visible text as the parser walks the document."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[LinkObservation] = []
        self._current_href: str | None = None
        self._current_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = href
            self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            text = "".join(self._current_text_parts).strip()
            self.links.append(LinkObservation(href=self._current_href, text=text))
            self._current_href = None
            self._current_text_parts = []


def extract_links(html: str) -> list[LinkObservation]:
    """
    Extract every anchor tag's href and visible text from an HTML
    document.

    Uses the standard library's html.parser rather than a full HTML
    parsing library (BeautifulSoup, lxml) or a regex -- regexes are
    notoriously unreliable for HTML, and stdlib's HTMLParser is
    tolerant of the malformed markup real-world sites often ship,
    without adding a new dependency for what is, so far, a single,
    narrow need: link discovery for the privacy-policy/ToS checks.

    Malformed input that HTMLParser can't process at all returns an
    empty list rather than raising -- a page PrivacyLens can't parse
    the links out of should read as "no matching link found" (a
    Potential Issue the relevant check reports), not as a scan
    failure.
    """
    parser = _AnchorExtractor()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - malformed HTML must not fail the scan
        return []
    return parser.links
