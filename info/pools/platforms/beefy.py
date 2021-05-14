from info.pools.pformat import PoolsInterface
from info.utils import fetch, helpers
from info.tokens import get_token_list
from pprint import pp
import asyncio
import dukpy

normal_pool_url = 'https://raw.githubusercontent.com/beefyfinance/beefy-app/master/src/features/configure/vault/bsc_pools.js'
special_pool_url = 'https://raw.githubusercontent.com/beefyfinance/beefy-app/master/src/features/configure/stake/bsc_stake.js'
apy_url = 'https://api.beefy.finance/apy'


class Beefy(PoolsInterface):
    apy_data = dict()  # for beefy only. beefy's apy data

    async def load_raw_format(self) -> list:
        self.raw_pools = []
        nm_pools, sp_pools = [], []

        pools_future = (fetch.get(normal_pool_url), fetch.get(special_pool_url), fetch.get(apy_url))
        nm_pools_raw, sp_pools_raw, apy_data = await asyncio.gather(*pools_future)

        bsc_tokens_list = await get_token_list()
        bsc_tokens_by_symbol = {token['currency']['symbol'].lower(): token for token in bsc_tokens_list}

        if nm_pools_raw.status == 200:
            try:
                source = nm_pools_raw.text.split("export const ")[1]
                nm_pools = dukpy.JSInterpreter().evaljs(source)
                for pool in nm_pools:
                    assets = [{
                        'symbol': bsc_tokens_by_symbol.get(asset.lower(), {}).get('currency', {}).get('symbol', '-'),
                        'address': bsc_tokens_by_symbol.get(asset.lower(), {}).get('currency', {}).get('address', '-')
                    } for asset in pool.get('assets', [])]

                    pool['assets'] = assets
            except:
                pass

        if sp_pools_raw.status == 200:  # BOOSTED
            try:
                source = sp_pools_raw.text.replace("govPoolABI", '"govPoolABI"').split("export const ")[1]
                sp_pools = dukpy.JSInterpreter().evaljs(source)
            except:
                pass

        if apy_data.status == 200:
            try:
                self.apy_data = apy_data.json
            except:
                pass

        # sp_pools reformat
        # sp_pools 의 경우 assets 따로 지정되어있지 않으며 stake 토큰이 earn token 으로 지정되어있으므로 재수정이 필요.
        nm_pools_dict = {pool['earnContractAddress']: pool for pool in nm_pools}
        nm_pools_token_dict = {pool.get('tokenAddress'): pool for pool in nm_pools}
        for sp_pool in sp_pools:
            sp_pool_token = sp_pool['tokenAddress']
            if nm_pools_dict.get(sp_pool_token):
                nm_pool = nm_pools_dict.get(sp_pool_token)
            else:
                nm_pool = nm_pools_token_dict.get(sp_pool_token)

            sp_pool['assets'] = nm_pool.get(sp_pool_token, '-')
            sp_pool['type'] = 'Special'

        self.raw_pools = nm_pools + sp_pools

    async def format_pools(self) -> list:
        def pool_formatter(pool):
            assets = pool.get('assets')
            is_special = pool.get('type') == 'Special'
            year_apy = self.apy_data.get(pool.get('id'), 0)
            year_apy = 0 if year_apy is None else year_apy
            if not is_special:
                name = "/".join(asset['symbol'] for asset in assets)
            else:
                name = f'Special {pool["token"]}'
                assets = [{
                    'symbol': pool.get('token'),
                    'address': pool.get('tokenAddress')
                }]
            return {
                'name': name,
                'address': pool.get('earnContractAddress'),
                # Future
                'apy': helpers.apy2apr(year_apy),
                'earn_token': [{
                    'symbol': pool.get('earnedOracleId') if is_special else pool.get('token'),
                    'address': pool.get('earnedTokenAddress') if is_special else pool.get('tokenAddress')
                }],
                'stake_token': {
                    'symbol': pool.get('token'),
                    'address': pool.get('tokenAddress')
                },
                'lp_ratio': [0, 0],
                'assets': assets,
                'is_vault': False if is_special else True,
                'pool_type': 'Special' if is_special else 'Normal'
            }

        raw_pools = self.raw_pools
        self.pools = {
            'Noraml': [pool_formatter(pool) for pool in raw_pools if pool.get('type') != 'Special'],
            'Special': [pool_formatter(pool) for pool in raw_pools if pool.get('type') == 'Special']
        }
