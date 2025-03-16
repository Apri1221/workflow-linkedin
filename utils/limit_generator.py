from fastapi import Request
from utils.ratelimit import Limiter
from utils.ip_address import get_ipaddr

# orchestrasi supaya ga buat satu satu di tiap router, utk bisa dipakai, dia harus pakai Request
limiter = Limiter(key_func=get_ipaddr, default_limits=["1/minute"], application_limits=["2/5seconds"])


@limiter.limit(limit_value="2/5seconds", error_message="cuk, udah melebihi limit")
async def rate_limited(request: Request):
    yield


@limiter.shared_limit(limit_value="5/second", scope="auth", error_message="Too many request, only 5 per second")
async def rate_limited_shared(request: Request):
    yield
