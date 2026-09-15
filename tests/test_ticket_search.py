"""Unit tests for the event ticket search tool."""

from unittest.mock import MagicMock, patch

from tools.ticket_search import search_event_tickets


class TestSearchEventTickets:
    """Test the search_event_tickets tool."""

    def test_returns_formatted_results_with_page_content(self):
        """Test that search results are formatted with title, link, and fetched page text."""
        fake_results = [
            {
                "title": "Beitar Jerusalem Official Site",
                "href": "https://www.beitarfc.co.il/",
                "body": "Next match info and tickets.",
            },
        ]

        with patch("tools.ticket_search.DDGS") as mock_ddgs_cls, \
             patch("tools.ticket_search._fetch_page_text", return_value="Ticket price: 80 NIS"):
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = fake_results
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            result = search_event_tickets.invoke({"event_query": "Beitar Jerusalem next game"})

        assert "Beitar Jerusalem Official Site" in result
        assert "https://www.beitarfc.co.il/" in result
        assert "Ticket price: 80 NIS" in result

    def test_falls_back_when_page_fetch_fails(self):
        """Test that a failed page fetch still returns the snippet/URL instead of crashing."""
        fake_results = [
            {"title": "Some Ticket Site", "href": "https://example.com", "body": "snippet text"},
        ]

        with patch("tools.ticket_search.DDGS") as mock_ddgs_cls, \
             patch("tools.ticket_search._fetch_page_text", return_value=""):
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = fake_results
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            result = search_event_tickets.invoke({"event_query": "some event"})

        assert "Some Ticket Site" in result
        assert "snippet text" in result
        assert "Could not fetch page content" in result

    def test_includes_query_in_search_terms(self):
        """Test that the event_query is passed through to the underlying search."""
        with patch("tools.ticket_search.DDGS") as mock_ddgs_cls, \
             patch("tools.ticket_search._fetch_page_text", return_value=""):
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = []
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            search_event_tickets.invoke({"event_query": "Hamilton show Tel Aviv"})

            called_query = mock_ddgs.text.call_args[0][0]
            assert "Hamilton show Tel Aviv" in called_query

    def test_no_results_found(self):
        """Test the message returned when the search yields no results."""
        with patch("tools.ticket_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = []
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            result = search_event_tickets.invoke({"event_query": "some obscure event"})

        assert "No results found" in result
        assert "some obscure event" in result

    def test_search_failure_is_handled_gracefully(self):
        """Test that an exception from the search backend doesn't propagate."""
        with patch("tools.ticket_search.DDGS") as mock_ddgs_cls:
            mock_ddgs_cls.return_value.__enter__.side_effect = Exception("network error")

            result = search_event_tickets.invoke({"event_query": "Beitar Jerusalem tickets"})

        assert "Ticket search failed" in result
        assert "network error" in result

    def test_extra_results_listed_without_fetching(self):
        """Test that results beyond PAGES_TO_FETCH are listed as plain links only."""
        fake_results = [
            {"title": f"Site {i}", "href": f"https://example.com/{i}", "body": f"snippet {i}"}
            for i in range(5)
        ]

        with patch("tools.ticket_search.DDGS") as mock_ddgs_cls, \
             patch("tools.ticket_search._fetch_page_text", return_value="fetched content") as mock_fetch:
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = fake_results
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            result = search_event_tickets.invoke({"event_query": "some event"})

        # Only the first PAGES_TO_FETCH (3) results should trigger a page fetch.
        assert mock_fetch.call_count == 3
        assert "Other results" in result
        assert "Site 4" in result
