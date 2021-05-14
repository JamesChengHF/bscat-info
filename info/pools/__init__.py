from info.pools.platforms import PLATFORMS
from info.utils.decorators import default_run
from info.tokens import update_token_list, get_token_list
from info.utils.db import cache
import asyncio
from time import time


# @default_run(dict())
async def load_pools_info():
    result = await asyncio.gather(*[platform.load() for platform in PLATFORMS])
    return {
        platform.__class__.__name__: pools_info
        for platform, pools_info in zip(PLATFORMS, result)
    }


@default_run(True)
async def update_pools():
    pools_info = await load_pools_info()
    if all(pools for platform, pools in pools_info.items()):
        await cache.set("pools", {
            'updated_at': int(time()),
            'data': pools_info
        })
    return True
