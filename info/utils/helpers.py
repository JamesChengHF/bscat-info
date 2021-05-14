def apy2apr(apy):
    if apy > 0:
        apy_daily = (365 * pow(1 + apy, 1 / 365) - 365) / 365 * 100
        apy = apy * 100
    else:
        apy_daily, apy = 0, 0
    return {
        'daily': apy_daily,
        'apr': apy_daily * 365 if apy_daily > 0 else 0,
        'year': apy
    }


def apr2apy(apr):
    if apr > 0:
        apy_daily = apr / 365 * 100
        apy = (pow((1 + (apr / 365)), 365) - 1) * 100
    else:
        apy_daily, apy = 0, 0
    return {
        'daily': apy_daily,
        'apr': apy_daily * 365 if apy_daily > 0 else 0,
        'year': apy
    }


async def future_matcher(obj, key):
    if obj.get(key):
        obj[key] = await obj.get(key)
    return True


async def target_future(future, target):
    target = await future
    return target
