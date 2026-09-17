# Run from repo root.

.PHONY: help sync dev-tester dev-worker

UV := uv run
APPS := $(CURDIR)/apps

help:
	@echo "Targets:"
	@echo "  make sync        - uv sync --all-groups"
	@echo "  make dev-tester  - Litestar tester (reload, :8000)"
	@echo "  make dev-worker  - Litestar worker (reload, :8001)"

sync:
	uv sync --all-groups

dev-tester:
	$(UV) --directory $(APPS)/tester python -m tester

dev-worker:
	$(UV) --directory $(APPS)/worker python -m worker
