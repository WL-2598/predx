"""全局配置：全部通过环境变量覆盖，便于容器化部署。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


class Config:
    APP_NAME = "PredX 事件合约交易所"
    VERSION = "1.0.0"
    ENGINE_VERSION = "1.0.0"

    # 存储
    DATA_DIR = Path(_env("PX_DATA_DIR", BASE_DIR / "data"))
    DB_PATH = Path(_env("PX_DB_PATH", DATA_DIR / "predx.db"))
    STATIC_DIR = Path(__file__).resolve().parent / "static"
    SEED_DIR = Path(__file__).resolve().parent / "seed"

    # 服务
    HOST = _env("PX_HOST", "0.0.0.0")
    PORT = int(_env("PX_PORT", "8100"))
    DEBUG = _env("PX_DEBUG", "0") == "1"

    # 安全
    SECRET_KEY = _env("PX_SECRET_KEY", "dev-only-change-me-in-production-0001")
    TOKEN_TTL_SECONDS = int(_env("PX_TOKEN_TTL", str(60 * 60 * 12)))
    PBKDF2_ROUNDS = int(_env("PX_PBKDF2_ROUNDS", "120000"))
    ALLOW_REGISTRATION = _env("PX_ALLOW_REGISTRATION", "1") == "1"

    # 限流（每 IP 每分钟）
    RATE_LIMIT_AUTH = int(_env("PX_RATE_LIMIT_AUTH", "20"))
    RATE_LIMIT_API = int(_env("PX_RATE_LIMIT_API", "300"))

    # ---------------------------------------------------------- 交易引擎
    # 手续费：吃单（taker）按成交额收取，做单免费（Polymarket 同款定价）
    TAKER_FEE_BPS = int(_env("PX_TAKER_FEE_BPS", "20"))     # 20 bps = 0.2%
    MIN_FEE_CENTS = 1
    # 价格单位为「分」，1 分 = 1% 概率；价格区间 [1, 99]
    PRICE_MIN = 1
    PRICE_MAX = 99
    # 单笔最小/最大下单量（份 = 合约张数，1 份结算价为 1 美元）
    MIN_QTY = 1
    MAX_QTY = int(_env("PX_MAX_QTY", "100000"))
    # LMSR 流动性深度（b 越大价格越稳）。每个市场可单独覆盖。
    DEFAULT_LMSR_B = float(_env("PX_LMSR_B", "1200"))
    # 新市场初始资金池补贴（分），用于做市商报价能力
    POOL_GRANT_CENTS = int(_env("PX_POOL_GRANT_CENTS", "2000000"))
    # 注册赠送体验金（分）
    SIGNUP_BONUS_CENTS = int(_env("PX_SIGNUP_BONUS_CENTS", "1000000"))
    # 做市机器人的报价档位（相对公允价）
    MAKER_SPREAD_CENTS = int(_env("PX_MAKER_SPREAD", "2"))
    MAKER_LEVELS = int(_env("PX_MAKER_LEVELS", "4"))
    MAKER_SIZE = int(_env("PX_MAKER_SIZE", "60"))

    SETTLEMENT_CURRENCY = "USD"
    SETTLEMENT_UNIT = "份"
    CONTRACT_PAYOUT_CENTS = 100        # 1 份合约结算价 = 1.00


config = Config()
config.DATA_DIR.mkdir(parents=True, exist_ok=True)
