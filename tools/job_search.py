"""Web search tool for LinkedIn job postings.

Searches public search engines for job listings indexed from linkedin.com,
rather than accessing LinkedIn directly — LinkedIn has no public API for job
search by individual developers, and scraping the site directly would violate
its Terms of Service.
"""

from ddgs import DDGS
from langchain_core.tools import tool

MAX_RESULTS = 8


@tool
def search_linkedin_jobs(job_query: str) -> str:
    """Search for job postings on LinkedIn matching a role, skill, or location.

    Use this whenever the user asks about job openings, career opportunities,
    or hiring on LinkedIn. `job_query` should describe the role as specifically
    as possible, e.g. "Python developer Tel Aviv" or "senior product manager
    remote fintech".

    Returns titles, links, and snippets of matching LinkedIn job postings found
    via web search (not a direct LinkedIn API, which isn't available to
    individual developers).
    """
    search_terms = f"site:linkedin.com/jobs {job_query}".strip()

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_terms, max_results=MAX_RESULTS))
    except Exception as e:
        return f"Job search failed: {e}"

    if not results:
        return f"No LinkedIn job postings found for: {job_query}"

    lines = []
    for r in results:
        title = (r.get("title") or "").strip()
        link = r.get("href") or r.get("link") or r.get("url") or ""
        snippet = (r.get("body") or "").strip()
        lines.append(f"- {title}\n  {link}\n  {snippet}")

    return "\n\n".join(lines)
