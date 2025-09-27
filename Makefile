.PHONY: dev ingest classify dashboard lint test

PYTHON=python3

export PYTHONPATH:=\"$(PWD)\"

install:
pip install -r requirements.txt

dev:
uvicorn app.main:app --reload --port 8000

ingest:
$(PYTHON) scripts/run_ingest.py

classify:
$(PYTHON) scripts/run_classify.py

dashboard:
streamlit run streamlit_app/app.py

lint:
mypy app

test:
pytest
