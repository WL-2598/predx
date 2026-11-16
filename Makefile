# ============================================================
#  PredX —— 常用命令（零依赖，make 只是记事的快捷方式）
# ============================================================
PY      ?= python3
PORT    ?= 8100
HOST    ?= 0.0.0.0
BASE    := http://127.0.0.1:$(PORT)

.PHONY: help init run test reset stats markets smoke clean backup

help:            ## 显示可用命令
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

init:            ## 建库 + 灌演示数据（幂等）
	$(PY) run.py --init-only

run:             ## 前台启动（0.0.0.0:8100）
	$(PY) run.py --host $(HOST) --port $(PORT)

test:            ## 单元/接口测试
	$(PY) -m pytest tests -q

reset:           ## 清库重建（危险：删除全部数据）
	$(PY) manage.py reset --yes

stats:           ## 平台概览
	$(PY) manage.py stats

markets:         ## 列出进行中的市场
	$(PY) manage.py markets --status open

smoke:           ## 起服务后跑一遍 HTTP 冒烟（需要服务已在运行）
	@echo "→ /api/markets"
	@curl -fsS "$(BASE)/api/markets?limit=1" > /dev/null && echo "  ok"
	@echo "→ /api/markets/stats"
	@curl -fsS "$(BASE)/api/markets/stats" > /dev/null && echo "  ok"
	@echo "→ /api/leaderboard"
	@curl -fsS "$(BASE)/api/leaderboard" > /dev/null && echo "  ok"
	@echo "→ 首页"
	@curl -fsS "$(BASE)/" > /dev/null && echo "  ok"
	@echo "→ 登录 demo@predx.io"
	@curl -fsS -X POST "$(BASE)/api/auth/login" -H 'Content-Type: application/json' \
		-d '{"email":"demo@predx.io","password":"demo1234"}' > /dev/null && echo "  ok"

backup:          ## 热备份数据库到 data/backup-*.db
	$(PY) -c "import shutil,time;from app.config import config;s='data/backup-%s.db'%time.strftime('%Y%m%d-%H%M%S');shutil.copy(config.DB_PATH,s);print('已备份 →',s)"

clean:           ## 清理缓存
	rm -rf __pycache__ app/**/__pycache__ tests/__pycache__ .pytest_cache
