from info.utils import fetch, helpers
from info.pools.pformat import PoolsInterface
from info.config import abi
from info.utils.bsc import Bsc
import asyncio, re, dukpy
from info.tokens import get_token_list
from pprint import pp
from time import time

"""
PancakeSwap

github - https://github.com/pancakeswap/pancake-frontend/
"""

URL = {
    'CAKE_FARMS': "https://raw.githubusercontent.com/pancakeswap/pancake-frontend/develop/src/config/constants/farms.ts",
    'CAKE_POOLS': "https://raw.githubusercontent.com/pancakeswap/pancake-frontend/develop/src/config/constants/pools.ts",
    'TOKENS': "https://api.pancakeswap.info/api/v2/tokens",
    'PAIRS': "https://api.pancakeswap.info/api/v2/pairs",
    'META': "https://raw.githubusercontent.com/pancakeswap/pancake-frontend/develop/src/config/index.ts"
}

MASTER_CHEF = "0x73feaa1eE314F8c655E354234017bE2193C9E24E"
CAKE_ADDRESS = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
WBNB_ADDRESS = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"


class PancakeSwap(PoolsInterface):
    async def load_raw_format(self) -> dict:
        cake_farms_raw, cake_pools_raw, cake_tokens_raw, cake_pairs_raw, cake_meta_raw = await asyncio.gather(
            *(
                fetch.get(URL['CAKE_FARMS']),
                fetch.get(URL['CAKE_POOLS']),
                fetch.get(URL['TOKENS']),
                fetch.get(URL['PAIRS']),
                fetch.get(URL['META'])
            )
        )

        cake_farms, cake_pools = [], []
        cake_tokens, cake_pairs = [], []
        cake_per_block = 0
        bsc_block_time = 0
        blocks_per_year = 0

        tokens_by_symbol = dict()
        syrup_cake_per_block = 0

        cake_price = 0
        bnb_price = 0

        bep_tokens = {
            token['currency']['symbol'].lower(): token['currency']
            for token in await get_token_list()
        }

        if cake_meta_raw.status == 200:
            raw_text = cake_meta_raw.text
            cake_per_block = int(re.findall("CAKE_PER_BLOCK = new BigNumber[(](\d{0,10})[)]", raw_text)[0])
            bsc_block_time = int(re.findall("BSC_BLOCK_TIME = (\d)", raw_text)[0])
            syrup_cake_per_block = int(
                re.findall("// (\d{1,5}) CAKE per block goes to CAKE syrup pool", raw_text)[0]) * 1e18
            blocks_per_year = 60 / bsc_block_time * 60 * 24 * 365

        if cake_farms_raw.status == 200:
            raw_data = cake_farms_raw.text

            # Modify tokens.[symbol] to 'symbol'
            cake_farms = re.sub("tokens[.](\w{0,15}),", "'\g<1>',", raw_data)

            # get only Object Part
            cake_farms = cake_farms.split("const farms: FarmConfig[] = ")[1].split("export default")[0]
            cake_farms = dukpy.evaljs(cake_farms)

            # set Assets
            for farm in cake_farms:
                farm['token'] = {
                    'symbol': bep_tokens.get(farm['token'], dict()).get('symbol', '-'),
                    'address': bep_tokens.get(farm['token'], dict()).get('address', '-'),
                }
                farm['quoteToken'] = {
                    'symbol': bep_tokens.get(farm['quoteToken'], dict()).get('symbol', '-'),
                    'address': bep_tokens.get(farm['quoteToken'], dict()).get('address', '-'),
                }

            # pp(cake_farms)

        if cake_pools_raw.status == 200:
            raw_data = cake_pools_raw.text

            # Modify tokens.symbol & poolCategory
            cake_pools = re.sub("tokens[.](\w{0,15}),", "'\g<1>',", raw_data)  # change token.symbol to 'symbol'
            cake_pools = re.sub("poolCategory:.{1,25},", "", cake_pools)

            # get only Object Part
            cake_pools = cake_pools.split("const pools: PoolConfig[] = ")[1].split("export default")[0]
            cake_pools = dukpy.evaljs(cake_pools)
            cake_pools = [pool for pool in cake_pools if not pool.get('isFinished', True)]

        if cake_pairs_raw.status == 200:
            cake_pairs = {pair['pair_address'].lower(): pair for _, pair in cake_pairs_raw.json['data'].items()}

        if cake_tokens_raw.status == 200:
            cake_price = float(cake_tokens_raw.json['data'].get(CAKE_ADDRESS)['price'])
            bnb_price = float(cake_tokens_raw.json['data'].get(WBNB_ADDRESS)['price'])
            tokens_by_symbol = {token['symbol'].lower(): dict(token, **{'address': addr})
                                for addr, token in cake_tokens_raw.json['data'].items()
                                }

        # calc APR
        bsc = Bsc()
        total_alloc = await bsc.call(**{
            'abi': abi.PANCAKE_MASTERCHEF,
            'contract': MASTER_CHEF,
            'function': 'totalAllocPoint'
        })
        if not total_alloc:
            return {'farms': [], 'pools': []}

        contract = await bsc.get_contract(**{
            'abi': abi.PANCAKE_MASTERCHEF,
            'address': MASTER_CHEF
        })

        farm_info_calls = [{
            'contract': contract,
            'function': 'poolInfo',
            'params': [farm['pid']]
        } for farm in cake_farms]

        farm_info_list = await bsc.contract_multi_call(*farm_info_calls)
        for farm, info in zip(cake_farms, farm_info_list):
            pool_weight = info[1] / total_alloc
            pair_liq = float(cake_pairs.get(farm['lpAddresses']['56'].lower(), dict()).get('liquidity', 0))
            try:
                apr = cake_per_block * blocks_per_year * pool_weight * cake_price / pair_liq * 100
            except Exception as e:
                apr = 0
            farm['apr'] = helpers.apr2apy(apr / 100)

        none_bnb_contract = await bsc.get_contract(abi.bep20, CAKE_ADDRESS)
        bnb_contract = await bsc.get_contract(abi.WBNB, WBNB_ADDRESS)

        checksums = await asyncio.gather(*[bsc.checksum(pool['contractAddress']['56']) for pool in cake_pools])
        for pool, chk in zip(cake_pools, checksums):
            pool['contract'] = chk if chk else "0x0000000000000000000000000000000000000000"

        pool_info_calls = [{
            'contract': bnb_contract if pool['stakingToken'] == 'bnb' else none_bnb_contract,
            'function': 'balanceOf',
            'params': [pool['contract']]
        } for pool in cake_pools]
        balance_data = await bsc.contract_multi_call(*pool_info_calls)
        for pool, balance in zip(cake_pools, balance_data):
            if pool['stakingToken'] == 'bnb':
                pool['balance'] = balance * bnb_price
            else:
                pool['balance'] = balance * cake_price
            reward_per_block = float(pool.get('tokenPerBlock')) * 1e18

            stake_token = tokens_by_symbol.get(pool['stakingToken'], dict())
            reward_token = tokens_by_symbol.get(pool['earningToken'], dict())
            pool['stakingToken'] = stake_token
            pool['earningToken'] = reward_token
            pool['tperblock'] = reward_per_block
            total_reward_price_per_year = float(reward_token.get('price', 0)) * reward_per_block * blocks_per_year
            pool['reward_balance'] = total_reward_price_per_year
            total_staking_token_in_pool = pool['balance']
            try:
                apr = total_reward_price_per_year / total_staking_token_in_pool * 100
            except:
                apr = 0
            pool['apr'] = helpers.apr2apy(round(apr, 3) / 1e2)

        self.raw_pools = {
            'farms': cake_farms,
            'pools': cake_pools

        }
        return []

    async def format_pools(self) -> list:
        async def format_farms(pool):
            tokens = await get_token_list()
            assets = [pool['token'], pool['quoteToken']]
            return {
                'name': "/".join([asset['symbol'] for asset in assets]),
                'pid': pool['pid'],
                'address': MASTER_CHEF,
                # Future
                'apy': 0,
                'earn_token': [{
                    'symbol': 'Cake',
                    'address': '0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82'
                }],
                'stake_token': {
                    'symbol': pool['lpSymbol'],
                    'address': pool['lpAddresses']['56']
                },
                'lp_ratio': [50, 50],
                'assets': assets,
                'is_vault': False,
                'pool_type': 'farm',
                'boost': None
            }

        async def format_pools(pool):
            return {
                'name': f"{pool['stakingToken']['symbol']} Earn {pool['earningToken']['symbol']}",
                'pid': pool['contractAddress']['56'],
                'address': pool['contractAddress']['56'],
                # Future
                'apy': 0,
                'earn_token': [{
                    'symbol': pool['earningToken']['symbol'],
                    'address': pool['earningToken']['address']
                }],
                'stake_token': {
                    'symbol': pool['stakingToken']['symbol'],
                    'address': pool['stakingToken']['address']
                },
                'lp_ratio': [0, 0],
                'assets': [
                    {
                        'symbol': pool['stakingToken']['symbol'],
                        'address': pool['stakingToken']['address']
                    }
                ],
                'is_vault': False,
                'pool_type': 'pool',
                'boost': None
            }

        raw_farms, raw_pools = self.raw_pools['farms'], self.raw_pools['pools']

        farms = [await format_farms(farm) for farm in raw_farms]
        pools = [await format_pools(pool) for pool in raw_pools if not pool['isFinished']]
        self.pools = {
            'farms': farms,
            'pools': pools
        }
        return self.pools
