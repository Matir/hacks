import aiohttp
from bs4 import BeautifulSoup

from .base import artifact_tool


@artifact_tool(max_chars=8000)
async def web_fetch(url: str) -> str:
    """Fetches the content of a web page and returns its text.

    Use this to read specific articles, documentation, or CVE details.

    Args:
        url: The URL of the page to fetch.

    Returns:
        The text content of the page (cleaned of HTML tags).
    """
    try:
        async with aiohttp.ClientSession() as session, session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:  # noqa: PLR2004
                return f"Error: Failed to fetch page, status code {response.status}"

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Get text and clean up whitespace
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            # We return the whole text, the artifact_tool will handle truncation if needed
            return text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"
