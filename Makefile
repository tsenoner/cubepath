# Cubepath — root task runner.
#
# This file is the single source of truth for the repo's command surface.
# The pre-push hook (.githooks/pre-push) and CI (.github/workflows/ci.yml)
# call these targets instead of re-listing commands, so the local gate and
# the CI gate cannot silently drift apart.
#
# Two gates, deliberately different:
#   make check  — fast; what the pre-push hook runs (no browser E2E)
#   make ci     — check + Playwright E2E; what GitHub Actions runs

APP := app
PY  := tools/diagrams

.DEFAULT_GOAL := help
.PHONY: help install dev preview diagrams cheatcards logo build build-guide build-app \
        check check-py check-app e2e ci clean

help: ## Show this help
	@echo "Cubepath — available targets:"
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*## ' $(MAKEFILE_LIST) \
		| sed 's/:.*## /|/' \
		| awk -F'|' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install app + Python dependencies
	cd $(APP) && npm ci
	cd $(PY) && uv sync

dev: ## Run the app dev server (http://localhost:4321)
	cd $(APP) && npm run dev

preview: ## Serve the built app locally
	cd $(APP) && npm run preview

diagrams: ## Regenerate SVG diagrams and sync them into the app
	cd $(PY) && uv run cubepath-diagrams
	bash scripts/sync-diagrams.sh

cheatcards: ## Generate the printable cheat card + print sheets, sync into the app
	cd $(PY) && uv run cubepath-cheatcards
	cp guide/build/cheat-card*.pdf $(APP)/public/

logo: ## Regenerate the brand mark (favicon.svg) and rasterize the icon set
	cd $(PY) && uv run cubepath-logo
	cd $(APP) && node scripts/gen-icons.mjs

build-guide: ## Build the PDF guide (diagrams + pandoc/typst)
	bash scripts/build.sh

build-app: ## Build the app
	cd $(APP) && npx astro build

build: build-guide cheatcards build-app ## Build everything (guide PDF + cards + app)

check-py: ## Python gate: ruff lint + format check + pytest
	cd $(PY) && uv run ruff check src/ tests/
	cd $(PY) && uv run ruff format --check src/ tests/
	cd $(PY) && uv run pytest tests/ -q

check-app: ## App gate: astro check + vitest + data verifiers + build
	@test -d $(APP)/node_modules || { echo "$(APP)/node_modules missing — run 'make install' first" >&2; exit 1; }
	cd $(APP) && npx astro check
	cd $(APP) && npx vitest run
	cd $(APP) && npm run verify:data
	cd $(APP) && npx astro build

check: check-py check-app ## Full local gate — what the pre-push hook runs

e2e: ## Playwright E2E (smoke + airplane-mode PWA gate)
	@test -d $(APP)/node_modules || { echo "$(APP)/node_modules missing — run 'make install' first" >&2; exit 1; }
	cd $(APP) && npx playwright test

ci: check e2e ## Everything CI runs

clean: ## Remove build output
	rm -rf $(APP)/dist $(APP)/.astro guide/build
