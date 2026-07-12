.PHONY: run run-dev venv install clean

VENV = .venv
PYTHON = $(VENV)/bin/python

venv:
	uv venv --python 3.12 $(VENV)

install: venv
	uv sync

run:
	$(PYTHON) websocket_server.py

run-dev:
	$(PYTHON) websocket_server.py --reload

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache
