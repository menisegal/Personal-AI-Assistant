"""Web search tool for event tickets (sports games, shows, concerts, etc.).

Beyond a plain web search, this fetches the actual content of the top result
pages so the agent can read real prices, dates, and availability instead of
just a search-engine snippet.
"""

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from langchain_core.tools import tool

MAX_RESULTS = 5
PAGES_TO_FETCH = 3
MAX_PAGE_CHARS = 2000
REQUEST_TIMEOUT = 8
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _fetch_page_text(url: str) -> str:
    """Fetch a URL and return its visible text, truncated. Empty string on failure."""
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())
    return text[:MAX_PAGE_CHARS]


@tool
def search_event_tickets(event_query: str) -> str:
    """Search the web for tickets to a sports game, show, concert, or other event,
    and fetch the actual ticket page content to find real prices and availability.

    Use this whenever the user asks about buying tickets, ticket prices, or an
    event's schedule. `event_query` should describe the event as specifically as
    possible, e.g. "Beitar Jerusalem next home game tickets" or "Hamilton show
    Tel Aviv tickets".

    Returns, for each of the top matching pages: its title, URL, and a chunk of
    the page's actual text content (where price/date/seat details usually are).
    """
    search_terms = f"{event_query} כרטיסים tickets".strip()

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_terms, max_results=MAX_RESULTS))
    except Exception as e:
        return f"Ticket search failed: {e}"

    if not results:
        return f"No results found for: {event_query}"

    sections = []
    for r in results[:PAGES_TO_FETCH]:
        title = (r.get("title") or "").strip()
        link = r.get("href") or r.get("link") or r.get("url") or ""
        snippet = (r.get("body") or "").strip()

        page_text = _fetch_page_text(link) if link else ""
        section = f"### {title}\nURL: {link}\nSearch snippet: {snippet}"
        if page_text:
            section += f"\nPage content: {page_text}"
        else:
            section += "\n(Could not fetch page content — rely on the snippet and URL above.)"
        sections.append(section)

    # Include any remaining results as plain links, without fetching, for extra context.
    extra = results[PAGES_TO_FETCH:MAX_RESULTS]
    if extra:
        extra_lines = "\n".join(
            f"- {(r.get('title') or '').strip()}: {r.get('href') or r.get('link') or r.get('url') or ''}"
            for r in extra
        )
        sections.append(f"### Other results\n{extra_lines}")

    return "\n\n".join(sections)
