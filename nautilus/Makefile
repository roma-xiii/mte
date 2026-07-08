.PHONY: run venv install clean

VENV = .venv
PYTHON = $(VENV)/bin/python

venv:
	uv venv --python 3.12 $(VENV)

install: venv
	uv pip install "nautilus_trader[visualization]" --python $(VENV)

run:
	$(PYTHON) backtest.py

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache
