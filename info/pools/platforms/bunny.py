from info.pools.pformat import PoolsInterface
from info.utils import fetch, helpers
from info.tokens import get_token_list
import re
import asyncio
import json
from pprint import pp

bunny_index = "https://pancakebunny.finance/pool"
bunny_apy = "https://firestore.googleapis.com/v1/projects/pancakebunny-finance/databases/(default)/documents/apy_data?pageSize=1000"


async def get_main_chunk():
    bunny_html = await fetch.get(bunny_index)
    tokens = dict()

    for token in await get_token_list():
        chk_token = tokens.get(token['currency']['symbol'])
        if chk_token and chk_token['count'] > token['count']:
            continue
        else:
            tokens[token['currency']['symbol'].lower()] = token
    tokens['bnb']['currency'] = {
        'address': '0x0000000000000000000000000000000000000000',
        'symbol': 'BNB'
    }

    if bunny_html.status != 200:
        return []

    re_main_chunk_id = re.compile('<script src="/static/js/main[.]([\w]*)[.]chunk[.]js">')
    re_main_data = re.compile(
        """e[.]exports=JSON[.]parse[(]'(.{0,100}"address":".{42}","token".*"type".{0,30})'[)]""")
    re_assets_data = re.compile("""e[.]exports=JSON[.]parse[(]'(.{0,200}"symbols":.*"index":.{0,40})'[)]""")

    chunk_id = re_main_chunk_id.findall(bunny_html.text)[0]
    chunk_js = (await fetch.get(f"https://pancakebunny.finance/static/js/main.{chunk_id}.chunk.js")).text

    pools_json = re_main_data.findall(chunk_js)[0]
    assets_json = re_assets_data.findall(chunk_js)[0]

    pools_data = json.loads(pools_json.replace("\\", ""))  # remove escape char
    pools_assets = json.loads(assets_json.replace("\\", ""))

    pools_data_by_addr = {pool['token'].lower(): pool for name, pool in pools_data.items()}
    pools_assets_by_addr = {asset.get('address', '').lower(): asset for name, asset in pools_assets.items()}

    for addr, data in pools_assets_by_addr.items():
        pd = pools_data_by_addr.get(addr, dict())
        pd.update({
            'assets': [
                {
                    'address': tokens.get(sym.lower())['currency']['address'] if tokens.get(sym.lower()) else '-',
                    'symbol': sym
                }
                for sym in data['symbols']
            ],
            'earn': [
                {
                    'symbol': sym,
                    'address': tokens.get(sym.lower())['currency']['address'] if tokens.get(sym.lower()) else '-'
                }
                for sym in pd.get('earn', "").split(" + ")
            ],
        })
    return [pool for _, pool in pools_data_by_addr.items()]


class PancakeBunny(PoolsInterface):
    async def load_raw_format(self) -> list:
        apy_info, pools_info = await asyncio.gather(*(fetch.get(bunny_apy), get_main_chunk()))
        if apy_info.status == 200:
            apy_info = {apy['fields']['pool']['stringValue'].lower(): float(apy['fields']['apy']['stringValue']) for apy
                        in
                        apy_info.json['documents']}
        else:
            apy_info = dict()

        for pool in pools_info:
            pool['apy'] = apy_info.get(pool['address'].lower(), 0)
        self.raw_pools = pools_info
        return self.raw_pools

    async def format_pools(self) -> list:
        def pool_formatter(pool):
            return {
                'name': "/".join([ass.get('symbol', '-') for ass in pool.get('assets', dict())]),
                'pid': pool.get('address'),
                'address': pool.get('address'),
                # Future
                'apy': helpers.apy2apr(pool.get('apy', 0)/1e2),
                'earn_token': pool['earn'],
                'stake_token': {
                    'symbol': "-".join([token['symbol'] for token in pool['assets']]),
                    'address': pool.get('lpToken')
                },
                'lp_ratio': [50, 50],
                'assets': pool.get('assets'),
                'is_vault': True if not pool.get('deposit') else False,
                'pool_type': '-',
                'boost': None
            }

        self.pools = [pool_formatter(pool) for pool in self.raw_pools]
        return self.pools
