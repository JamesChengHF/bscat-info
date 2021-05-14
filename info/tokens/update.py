from info.utils.bitquery import send_query
from info.tokens.query import bsc_token_list_query
from info.utils.decorators import default_run
from info.utils.db import cache
from aiocache import cached
from time import time
import os

cwd = os.path.dirname(__file__)
db_path = os.path.join(cwd, 'tokens.json')


async def _get_tokens_list():
    token_list = await send_query(bsc_token_list_query)
    if token_list.status == 200:
        data = token_list.json
        token_transfers = data['data'].get('ethereum', dict()).get('transfers')
        return [token for token in token_transfers if token.get('count', 0) > 5000]
    else:
        return []

@default_run(True)
async def update_token_list():
    token_list = await _get_tokens_list()

    if not token_list:
        return False

    for token in token_list:
        if token['currency']['symbol'].lower() == 'bnb':
            token = {
                'currency': {
                    'address': '0x0000000000000000000000000000000000000000',
                    'symbol': 'BNB'
                },
                'count': 1000000000
            }
            break

    await cache.set("bep_tokens", {
        'updated_at': int(time()),
        'data': token_list
    })
    return True


@cached(ttl=60 * 60 * 2)
@default_run(default=[])
async def get_token_list():
    token_list = await cache.get("bep_tokens")
    return token_list.get('data', []) if token_list else []
