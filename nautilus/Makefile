.PHONY: run venv install clean

VENV = .venv
PYTHON = $(VENV)/bin/python

venv:
	uv venv --python 3.12 $(VENV)

install: venv
	uv sync

run:
	$(PYTHON) websocket_server.py

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache
