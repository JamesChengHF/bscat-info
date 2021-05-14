from chalice import Chalice, Rate
from info.tokens import update_token_list
from info.pools import update_pools
import asyncio

app = Chalice(app_name='bscat-info')


@app.route('/')
def index():
    return {'hello': 'world'}


@app.schedule(Rate(1, unit=Rate.DAYS))
def update_tokens():
    return asyncio.run(update_token_list())


@app.schedule(Rate(2, unit=Rate.HOURS))
def update_pools_list():
    return asyncio.run(update_pools())
