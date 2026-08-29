# RailTwin-X v4 — Root Makefile
# SIH 2026 PS 26028 · Delay Intelligence Engine
# Usage: make <target>

.PHONY: help install seed seed-mixed train eval test nightly api drift clean docker-build docker-up docker-down

PYTHON := python
PYTEST := python -m pytest

##──────────────────────────────────────────────────────────────
## Help
##──────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "RailTwin-X v4 — Available Make Targets"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  install        Install Python dependencies"
	@echo "  seed           Seed DB (passenger network)"
	@echo "  seed-mixed     Seed DB (mixed passenger+DFC)"
	@echo "  train          Retrain LightGBM ensemble + CQR"
	@echo "  train-gru      Retrain PyTorch GRU champion"
	@echo "  eval           Run held-out evaluation (F14 proof table)"
	@echo "  drift          Run PSI feature drift monitor"
	@echo "  nightly        Run full nightly pipeline (seed+train+eval+drift)"
	@echo "  nightly-fast   Nightly without GRU retrain (faster CI)"
	@echo "  test           Run full pytest suite (78 tests)"
	@echo "  api            Start dev API server (localhost:8000)"
	@echo "  docker-build   Build Docker image railtwin-x:v4"
	@echo "  docker-up      Start production stack (docker-compose)"
	@echo "  docker-down    Stop production stack"
	@echo "  clean          Remove cached artifacts (parquet, model files)"
	@echo ""

##──────────────────────────────────────────────────────────────
## Setup
##──────────────────────────────────────────────────────────────
install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "[OK] Dependencies installed."

##──────────────────────────────────────────────────────────────
## Data
##──────────────────────────────────────────────────────────────
seed:
	$(PYTHON) -m data.seed --network=passenger

seed-mixed:
	$(PYTHON) -m data.seed --network=mixed

##──────────────────────────────────────────────────────────────
## ML Pipeline
##──────────────────────────────────────────────────────────────
train:
	$(PYTHON) -m ml.train

train-gru:
	$(PYTHON) -m ml.model_seq

ensemble:
	$(PYTHON) -m ml.ensemble

eval:
	$(PYTHON) -m ml.evaluate

drift:
	$(PYTHON) -m ml.drift

##──────────────────────────────────────────────────────────────
## Full Nightly Pipeline
##──────────────────────────────────────────────────────────────
nightly:
	$(PYTHON) -m scripts.nightly_pipeline --network=mixed

nightly-fast:
	$(PYTHON) -m scripts.nightly_pipeline --network=mixed --skip-gru

##──────────────────────────────────────────────────────────────
## Testing
##──────────────────────────────────────────────────────────────
test:
	$(PYTEST) tests/ -q

test-verbose:
	$(PYTEST) tests/ -v

test-api:
	$(PYTEST) tests/test_api.py -v

test-ml:
	$(PYTEST) tests/test_ml.py tests/test_model_accuracy.py -v

test-e2e:
	$(PYTEST) tests/test_brain_e2e_adversarial.py tests/test_e2e_demo.py -v

##──────────────────────────────────────────────────────────────
## API Server
##──────────────────────────────────────────────────────────────
api:
	$(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

api-prod:
	$(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2

##──────────────────────────────────────────────────────────────
## Docker
##──────────────────────────────────────────────────────────────
docker-build:
	docker build -t railtwin-x:v4 .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

##──────────────────────────────────────────────────────────────
## Cleanup
##──────────────────────────────────────────────────────────────
clean:
	@echo "[INFO] Cleaning cached artifacts..."
	-rm -f artifacts/model_*.txt artifacts/model_*.pkl
	-rm -f artifacts/metrics.json artifacts/drift_report.json
	-rm -rf data/cache/*.parquet
	@echo "[OK] Cache cleaned. Run 'make train eval' to rebuild."

clean-db:
	@echo "[WARN] This will DELETE the database. Run 'make seed' to rebuild."
	-rm -f data/railtwin.db
