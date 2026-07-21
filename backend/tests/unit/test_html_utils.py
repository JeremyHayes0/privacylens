from app.scanning.html_utils import extract_links


def test_extracts_href_and_text_from_simple_anchor():
    html = '<html><body><a href="/privacy">Privacy Policy</a></body></html>'
    links = extract_links(html)

    assert len(links) == 1
    assert links[0].href == "/privacy"
    assert links[0].text == "Privacy Policy"


def test_extracts_multiple_links_in_document_order():
    html = """
        <footer>
            <a href="/privacy">Privacy</a>
            <a href="/terms">Terms</a>
        </footer>
    """
    links = extract_links(html)

    assert [link.href for link in links] == ["/privacy", "/terms"]
    assert [link.text for link in links] == ["Privacy", "Terms"]


def test_anchor_with_no_href_is_ignored():
    html = '<a name="anchor-only">Not a link</a><a href="/real">Real link</a>'
    links = extract_links(html)

    assert len(links) == 1
    assert links[0].href == "/real"


def test_anchor_with_no_visible_text_has_empty_text():
    html = '<a href="/icon-link"><img src="icon.png"></a>'
    links = extract_links(html)

    assert len(links) == 1
    assert links[0].text == ""


def test_malformed_html_does_not_raise():
    """A page PrivacyLens can't parse should look like 'no links found,' not crash the scan."""
    links = extract_links("<a href='/unterminated <div><span>broken")
    assert isinstance(links, list)


def test_empty_document_returns_no_links():
    assert extract_links("<html><body>No links here.</body></html>") == []
