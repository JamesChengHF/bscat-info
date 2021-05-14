from time import time
from pprint import pp
from info.utils.bsc import Bsc
from info.utils.decorators import default_run
from typing import Union
import asyncio


class PoolsInterface:
    raw_pools: Union[list, dict]
    pools: Union[list, dict]
    bsc = Bsc()

    async def load(self) -> dict:
        await self.load_raw_format()
        await self.format_pools()
        return self.pools

    async def load_raw_format(self) -> list:
        raise NotImplementedError

    async def format_pools(self) -> list:
        raise NotImplementedError

    def test(self, output=False):
        async def _test():
            fs = [self.load_raw_format, self.format_pools]
            for f in fs:
                start = time()
                res = await f()
                if output:
                    pp(res)
                end = time() - start
                print(f"{f.__name__} => time: {round(end, 3)} .sec")

        asyncio.run(_test())
