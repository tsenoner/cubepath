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
PY  := tools/cubepath

.DEFAULT_GOAL := help
.PHONY: help install dev preview diagrams cards cheatcards logo build build-guide build-app \
        fmt check check-py check-app e2e ci clean

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

cheatcards: cards ## Deprecated alias for `cards`

cards: ## Generate the printable card set + print sheets, sync into the app
	cd $(PY) && uv run cubepath-cards
	rm -rf $(APP)/public/cards && mkdir -p $(APP)/public/cards
	cp guide/build/cards/*.pdf $(APP)/public/cards/

logo: ## Regenerate the brand mark (favicon.svg) and rasterize the icon set
	cd $(PY) && uv run cubepath-logo
	cd $(APP) && node scripts/gen-icons.mjs

build-guide: diagrams ## Build the PDF guide (pandoc/typst) and ship it into the app
	bash scripts/build.sh

build-app: ## Build the app
	cd $(APP) && npx astro build

build: build-guide cards build-app ## Build everything (diagrams + guide PDF + cards + app)

fmt: ## Apply every formatter/autofix in the repo
	cd $(APP) && npx prettier --write .
	cd $(APP) && npx eslint . --fix
	cd $(PY) && uv run ruff check --fix src/ tests/
	cd $(PY) && uv run ruff format src/ tests/

check-py: ## Python gate: ruff lint + format check + mypy + pytest
	cd $(PY) && uv run ruff check src/ tests/
	cd $(PY) && uv run ruff format --check src/ tests/
	cd $(PY) && uv run mypy
	cd $(PY) && uv run pytest tests/ -q

check-app: ## App gate: format + lint + types (incl. scripts) + vitest + data verifiers + build
	@test -d $(APP)/node_modules || { echo "$(APP)/node_modules missing — run 'make install' first" >&2; exit 1; }
	cd $(APP) && npx prettier --check .
	cd $(APP) && npx eslint .
	cd $(APP) && npx astro check
	cd $(APP) && npm run check:scripts
	cd $(APP) && npx vitest run
	cd $(APP) && npm run verify:data
	cd $(APP) && npx astro build

check: check-py check-app ## Full local gate — what the pre-push hook runs

e2e: ## Playwright E2E (smoke + airplane-mode PWA gate)
	@test -d $(APP)/node_modules || { echo "$(APP)/node_modules missing — run 'make install' first" >&2; exit 1; }
	cd $(APP) && npx playwright test

ci: check e2e ## Everything CI runs

clean: ## Remove build output
	rm -rf $(APP)/dist $(APP)/.astro .astro guide/build
