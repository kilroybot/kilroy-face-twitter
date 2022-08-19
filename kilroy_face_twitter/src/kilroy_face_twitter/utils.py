from pathlib import Path
from urllib.parse import urlparse

import httpx


async def download_image(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content


def get_filename_from_url(url: str) -> str:
    return Path(urlparse(url).path).name
