.PHONY: help install train pipeline api dashboard signals test lint

LEADS ?= data/real_leads.csv

help:  ## List available commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

install:  ## Install runtime + dev dependencies
	pip install -r requirements.txt -r requirements-dev.txt

train:  ## Train the ICP model (writes model/icp_model.json)
	python train_model.py

pipeline:  ## Score + draft outreach for LEADS (default data/real_leads.csv)
	python run_pipeline.py $(LEADS)

api:  ## Run the FastAPI service at http://127.0.0.1:8000
	uvicorn app.main:app --reload

dashboard:  ## Run the Streamlit dashboard
	streamlit run dashboard.py

signals:  ## Check public news signals for LEADS
	python check_signals.py $(LEADS)

test:  ## Run the test suite
	python -m pytest tests/ -q

lint:  ## Lint with ruff
	ruff check .
