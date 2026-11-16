#!/usr/bin/env python3
"""启动入口：python3 run.py [--init-only] [--port 8100]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="PredX 事件合约交易所")
    parser.add_argument("--init-only", action="store_true", help="只建库灌数据，不启服务")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    from app.config import config
    if args.host:
        config.HOST = args.host
    if args.port:
        config.PORT = args.port

    if args.init_only:
        from app.seed import bootstrap
        bootstrap()
        print(f"数据库：{config.DB_PATH}")
        return

    from app.main import run
    run()


if __name__ == "__main__":
    main()
