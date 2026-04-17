import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from trashdig.tools.web_fetch import web_fetch

@pytest.mark.anyio
@patch("aiohttp.ClientSession.get")
async def test_web_fetch(mock_get):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html><body><h1>Hello</h1></body></html>")

    # aiohttp uses async context managers
    mock_get.return_value.__aenter__.return_value = mock_response

    result = await web_fetch("http://example.com")
    assert "Hello" in result
