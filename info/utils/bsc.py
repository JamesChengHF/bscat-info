from web3 import Web3, HTTPProvider
from web3.types import RPCEndpoint, RPCResponse, Any
from info.config.abi import lps, bep20
from sqlalchemy.util import await_only
from eth_typing import URI
from functools import partial
from random import randint
from typing import Union
import aiohttp
import sys
import asyncio
import greenlet

w3 = Web3(Web3.HTTPProvider('https://bsc-dataseed1.binance.org/'))

BSC_PROVIDERS = """https://bsc-dataseed1.binance.org/
https://bsc-dataseed2.binance.org/
https://bsc-dataseed3.binance.org/
https://bsc-dataseed4.binance.org/"""


class Bsc:
    def __init__(self):
        self._w3 = [Web3(HTTPProvider(prov)) for prov in BSC_PROVIDERS.split('\n')]

    @property
    def w3(self):
        rpc_id = randint(0, len(self._w3) - 1)
        return self._w3[rpc_id]

    async def checksum(self, addr):
        loop = asyncio.get_running_loop()

        try:
            return await loop.run_in_executor(None, partial(self.w3.toChecksumAddress, addr))
        except:
            return False

    async def call(self, abi, contract, function, params: Union[None, list] = None):
        loop = asyncio.get_running_loop()

        try:
            contract_address = await loop.run_in_executor(None, partial(self.w3.toChecksumAddress, contract))
        except:
            return False

        contract_params = {
            'address': contract_address,
            'abi': str(abi)
        }
        contract = await loop.run_in_executor(None, partial(self.w3.eth.contract, **contract_params))
        try:
            if params:
                result = await loop.run_in_executor(None, contract.functions[function](*params).call)
            else:
                result = await loop.run_in_executor(None, contract.functions[function]().call)
            return result
        except Exception as e:
            print(e, contract.address)
            return False

    async def multi_call(self, *calls: dict):
        return await asyncio.gather(*[self.call(**call) for call in calls])

    async def get_contract(self, abi, address):
        loop = asyncio.get_running_loop()
        try:
            contract_address = await loop.run_in_executor(None, partial(self.w3.toChecksumAddress, address))
        except:
            return False

        contract_params = {
            'address': contract_address,
            'abi': str(abi)
        }
        contract = await loop.run_in_executor(None, partial(self.w3.eth.contract, **contract_params))
        return contract

    async def contract_call(self, contract, function, params):
        loop = asyncio.get_running_loop()
        try:
            if params:
                result = await loop.run_in_executor(None, contract.functions[function](*params).call)
            else:
                result = await loop.run_in_executor(None, contract.functions[function]().call)
            return result
        except Exception as e:
            return False

    async def contract_multi_call(self, *calls):
        return await asyncio.gather(*[self.contract_call(**call) for call in calls])
