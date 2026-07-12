# Apple Watch Health Metrics — common workflows
VENV := .venv/bin
EXPORT ?= apple_health_export/export.xml

.PHONY: setup ingest serve frontend test clean

setup:            ## create venv + install backend deps + frontend deps
	python3 -m venv .venv
	$(VENV)/pip install -r requirements.txt
	cd frontend && npm install

ingest:           ## run the pipeline: export.xml -> bronze -> silver -> gold
	$(VENV)/python -m pipeline.run --input $(EXPORT)

serve:            ## run the API locally (dev)
	PORT=5001 $(VENV)/python -m api.app

serve-prod:       ## run the API under gunicorn
	$(VENV)/gunicorn -w 2 -b 0.0.0.0:$${PORT:-5001} api.app:app

frontend:         ## run the Vite dev server (proxies /api to :5001)
	cd frontend && npm run dev

test:             ## run the test suite
	$(VENV)/python -m pytest tests/ -q

clean:            ## delete all derived data (bronze/silver/gold/quality)
	rm -rf data/
