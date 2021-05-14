from .beefy import Beefy
from .pancakeswap import PancakeSwap
from .bunny import PancakeBunny

PLATFORMS = [
    Beefy(),
    PancakeSwap(),
    PancakeBunny()
]
