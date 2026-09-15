"""Unit tests for the LinkedIn job search tool."""

from unittest.mock import MagicMock, patch

from tools.job_search import search_linkedin_jobs


class TestSearchLinkedinJobs:
    """Test the search_linkedin_jobs tool."""

    def test_returns_formatted_results(self):
        """Test that job results are formatted with title, link, and snippet."""
        fake_results = [
            {
                "title": "Senior Python Developer at EverC",
                "href": "https://il.linkedin.com/jobs/view/senior-python-developer-at-everc-123",
                "body": "Tel Aviv-Yafo, Israel. Backend team.",
            },
        ]

        with patch("tools.job_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = fake_results
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            result = search_linkedin_jobs.invoke({"job_query": "Python developer Tel Aviv"})

        assert "Senior Python Developer at EverC" in result
        assert "https://il.linkedin.com/jobs/view/senior-python-developer-at-everc-123" in result
        assert "Tel Aviv-Yafo" in result

    def test_search_is_scoped_to_linkedin_jobs(self):
        """Test that the search query is restricted to linkedin.com/jobs."""
        with patch("tools.job_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = []
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            search_linkedin_jobs.invoke({"job_query": "product manager remote"})

            called_query = mock_ddgs.text.call_args[0][0]
            assert "site:linkedin.com/jobs" in called_query
            assert "product manager remote" in called_query

    def test_no_results_found(self):
        """Test the message returned when no job postings match."""
        with patch("tools.job_search.DDGS") as mock_ddgs_cls:
            mock_ddgs = MagicMock()
            mock_ddgs.text.return_value = []
            mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs

            result = search_linkedin_jobs.invoke({"job_query": "underwater basket weaver"})

        assert "No LinkedIn job postings found" in result
        assert "underwater basket weaver" in result

    def test_search_failure_is_handled_gracefully(self):
        """Test that an exception from the search backend doesn't propagate."""
        with patch("tools.job_search.DDGS") as mock_ddgs_cls:
            mock_ddgs_cls.return_value.__enter__.side_effect = Exception("network error")

            result = search_linkedin_jobs.invoke({"job_query": "data scientist"})

        assert "Job search failed" in result
        assert "network error" in result
