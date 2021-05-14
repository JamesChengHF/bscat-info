import aiohttp
from collections import namedtuple

resp = namedtuple('response', 'status,json,text')


async def get(*args, **kwargs) -> resp:
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(*args, **kwargs) as response:
            try:
                resp_json = await response.json()
            except Exception as e:
                resp_json = False
            return resp(response.status, resp_json, await response.text())


async def post(*args, **kwargs) -> resp:
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(*args, **kwargs) as response:
            try:
                resp_json = await response.json()
            except Exception as e:
                resp_json = False
            return resp(response.status, resp_json, await response.text())
