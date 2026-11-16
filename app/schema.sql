-- ============================================================
-- PredX 事件合约交易所 · 数据库结构 v1.0
-- 金额一律用「分」（整数），价格用「分/份」（1 分 = 1% 概率）
-- 1 份合约到期结算价 = 100 分（1.00 美元）
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    handle        TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'trader',   -- trader|creator|admin|liquidity
    status        TEXT    NOT NULL DEFAULT 'active',   -- active|frozen
    balance_cents INTEGER NOT NULL DEFAULT 0,
    equity_seed   INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS markets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    slug           TEXT    NOT NULL UNIQUE,
    question       TEXT    NOT NULL,
    description    TEXT,
    rules          TEXT,                                -- 结算规则（判定标准）
    category       TEXT    NOT NULL DEFAULT '综合',
    market_type    TEXT    NOT NULL DEFAULT 'binary',   -- binary|multi
    status         TEXT    NOT NULL DEFAULT 'open',     -- open|closed|resolved|cancelled
    emoji          TEXT,
    closes_at      TEXT,                                -- 停止交易时间
    resolve_by     TEXT,                                -- 预计结算时间
    source_url     TEXT,                                -- 结算依据来源
    liquidity_b    REAL    NOT NULL DEFAULT 1200,
    fee_bps        INTEGER NOT NULL DEFAULT 20,
    volume_cents   INTEGER NOT NULL DEFAULT 0,
    trades_count   INTEGER NOT NULL DEFAULT 0,
    featured       INTEGER NOT NULL DEFAULT 0,
    created_by     INTEGER,
    created_at     TEXT    NOT NULL,
    closed_at      TEXT,
    resolved_at    TEXT,
    resolution_outcome_id INTEGER,
    resolution_note TEXT
);
CREATE INDEX IF NOT EXISTS idx_markets_status ON markets(status, closes_at);
CREATE INDEX IF NOT EXISTS idx_markets_cat ON markets(category);

CREATE TABLE IF NOT EXISTS outcomes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id          INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    seq                INTEGER NOT NULL,
    name               TEXT    NOT NULL,
    lmsr_q             REAL    NOT NULL DEFAULT 0,      -- LMSR 状态变量
    shares_outstanding INTEGER NOT NULL DEFAULT 0,
    last_price_cents   INTEGER NOT NULL DEFAULT 50,
    prev_price_cents   INTEGER NOT NULL DEFAULT 50,
    is_winner          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_outcomes_market ON outcomes(market_id, seq);

CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    market_id      INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    outcome_id     INTEGER NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    side           TEXT    NOT NULL,                    -- buy|sell
    order_type     TEXT    NOT NULL DEFAULT 'limit',    -- limit|market
    price_cents    INTEGER NOT NULL,
    qty            INTEGER NOT NULL,
    filled_qty     INTEGER NOT NULL DEFAULT 0,
    avg_fill_cents REAL    NOT NULL DEFAULT 0,
    status         TEXT    NOT NULL DEFAULT 'open',     -- open|filled|cancelled|rejected
    reserved_cents INTEGER NOT NULL DEFAULT 0,
    taker_fee_cents INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_book
    ON orders(market_id, outcome_id, side, status, price_cents, id);

CREATE TABLE IF NOT EXISTS trades (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id     INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    outcome_id    INTEGER NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    price_cents   INTEGER NOT NULL,
    qty           INTEGER NOT NULL,
    notional_cents INTEGER NOT NULL,
    buyer_id      INTEGER,
    seller_id     INTEGER,                              -- NULL = 流动性池
    buy_order_id  INTEGER,
    sell_order_id INTEGER,
    taker_side    TEXT    NOT NULL DEFAULT 'buy',
    fee_cents     INTEGER NOT NULL DEFAULT 0,
    source        TEXT    NOT NULL DEFAULT 'book',      -- book|amm
    created_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(buyer_id, seller_id);

CREATE TABLE IF NOT EXISTS positions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    market_id      INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    outcome_id     INTEGER NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    shares         INTEGER NOT NULL DEFAULT 0,
    locked_shares  INTEGER NOT NULL DEFAULT 0,          -- 挂单冻结（卖出挂单）
    cost_cents     INTEGER NOT NULL DEFAULT 0,          -- 持仓成本（含手续费）
    realized_cents INTEGER NOT NULL DEFAULT 0,
    updated_at     TEXT    NOT NULL,
    UNIQUE(user_id, outcome_id)
);
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id, market_id);

CREATE TABLE IF NOT EXISTS ledger (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind                TEXT    NOT NULL,               -- signup|deposit|trade_buy|trade_sell|fee|reward|payout|refund
    delta_cents         INTEGER NOT NULL,
    balance_after_cents INTEGER NOT NULL,
    market_id           INTEGER,
    ref                 TEXT,
    note                TEXT,
    created_at          TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ledger_user ON ledger(user_id, id DESC);

CREATE TABLE IF NOT EXISTS price_points (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id   INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    outcome_id  INTEGER NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    price_cents INTEGER NOT NULL,
    ts          TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_price_points ON price_points(market_id, outcome_id, id);

CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id  INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body       TEXT    NOT NULL,
    parent_id  INTEGER,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_market ON comments(market_id, id DESC);

CREATE TABLE IF NOT EXISTS watchlist (
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    market_id INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id, market_id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT    NOT NULL,
    prefix       TEXT    NOT NULL,
    key_hash     TEXT    NOT NULL,
    revoked      INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL,
    last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    action     TEXT    NOT NULL,
    target     TEXT,
    meta       TEXT,
    ip         TEXT,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(id DESC);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
