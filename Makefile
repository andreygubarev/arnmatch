.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: lint
lint: ## Run linter
	uv run ruff check .

.PHONY: check
check: lint ## Run lint and test

.PHONY: build
build: ## Build package
	uv build

.PHONY: clean
clean: ## Clean build artifacts
	rm -rf dist/ __pycache__/ .pytest_cache/ .ruff_cache/
