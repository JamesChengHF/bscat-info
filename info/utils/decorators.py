from functools import wraps

def default_run(default=False, print_except=False):
    def wrapper(f):
        @wraps(f)
        async def wrapped(*args, **kwargs):
            try:
                return await f(*args, **kwargs)
            except Exception as e:
                if print_except:
                    print(e)
                return default
        return wrapped
    return wrapper
