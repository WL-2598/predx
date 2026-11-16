"""路由汇总。"""
from . import admin, auth, markets, portfolio, social, trading


def register_routes(r):
    auth.register_routes(r)
    markets.register_routes(r)
    trading.register_routes(r)
    portfolio.register_routes(r)
    social.register_routes(r)
    admin.register_routes(r)
    return r
