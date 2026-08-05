from unittest.mock import patch

from app.adapters.documentation.client import NRPDocumentationClient


def test_documentation_client_returns_ranked_official_page_excerpts() -> None:
    client = NRPDocumentationClient(
        documentation_url="https://docs.example.test/documentation/",
        timeout_seconds=1,
        max_results=1,
    )
    client._fetch = lambda url: (  # type: ignore[method-assign]
        url,
        (
            "<html><title>Documentation</title><body>"
            '<a href="/documentation/storage/">Storage guide</a>'
            '<a href="https://untrusted.example.test/">Outside link</a>'
            "</body></html>"
            if url == "https://docs.example.test/documentation/"
            else "<html><title>Storage guide</title><main>"
            "Use persistent volumes for storage."
            "</main></html>"
        ),
    )

    pages = client.search("How do I use storage?")

    assert len(pages) == 1
    assert pages[0].title == "Storage guide"
    assert str(pages[0].url) == "https://docs.example.test/documentation/storage/"
    assert pages[0].excerpt == "Use persistent volumes for storage."


def test_documentation_client_ranks_page_content_and_headings_higher_than_link_title() -> (
    None
):
    client = NRPDocumentationClient(
        documentation_url="https://docs.example.test/documentation/",
        timeout_seconds=1,
        max_results=1,
    )

    def fetch(url: str) -> tuple[str, str]:
        if url == "https://docs.example.test/documentation/":
            return (
                url,
                (
                    "<html><title>Documentation</title><body>"
                    '<a href="/documentation/overview/">Overview</a>'
                    '<a href="/documentation/storage/">Storage guide</a>'
                    "</body></html>"
                ),
            )
        if url == "https://docs.example.test/documentation/overview/":
            return (
                url,
                "<html><title>Overview</title><main>Learn how to use storage and GPU resources.</main></html>",
            )
        return (
            url,
            "<html><title>Storage guide</title><main>Persistent volumes help store data.</main></html>",
        )

    client._fetch = fetch  # type: ignore[method-assign]

    pages = client.search("storage resources")

    assert len(pages) == 1
    assert pages[0].title == "Overview"
    assert str(pages[0].url) == "https://docs.example.test/documentation/overview/"
    assert "storage" in pages[0].excerpt


def test_documentation_client_emits_debug_events_without_query_content() -> None:
    client = NRPDocumentationClient(
        documentation_url="https://docs.example.test/documentation/",
        timeout_seconds=1,
        max_results=1,
    )
    client._fetch = lambda url: (  # type: ignore[method-assign]
        url,
        "<html><title>Documentation</title><body>"
        '<a href="/documentation/gpu/">GPU pods</a>'
        "</body></html>"
        if url == "https://docs.example.test/documentation/"
        else "<html><title>GPU pods</title><main>Request a GPU.</main></html>",
    )

    with patch("app.adapters.documentation.client.logger") as logger:
        client.search("private workload details about GPUs")

    events = [call.args[0] for call in logger.debug.call_args_list]
    assert "nrp_documentation_search_started" in events
    assert "nrp_documentation_links_discovered" in events
    assert "nrp_documentation_links_ranked" in events
    assert "nrp_documentation_page_parsed" in events
    assert "nrp_documentation_search_completed" in events
    assert "nrp_documentation_pages_scored" in events
    assert logger.debug.call_args_list[0].kwargs["query_length"] == 35
    assert "query" not in logger.debug.call_args_list[0].kwargs
