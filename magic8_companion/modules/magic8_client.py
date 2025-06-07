import json
import aiohttp
import aiofiles
from ..config import settings

async def fetch_from_file(path: str):
    try:
        async with aiofiles.open(path, 'r') as f:
            data = await f.read()
        return json.loads(data)
    except FileNotFoundError:
        return None

async def fetch_from_http(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None

async def get_latest_magic8_data():
    """Retrieve latest Magic8 prediction based on settings"""
    if settings.magic8_source == 'file':
        return await fetch_from_file(settings.magic8_file_path)
    if settings.magic8_source == 'http':
        return await fetch_from_http(settings.magic8_url)
    return None
