SHELL := /bin/bash

SCENARIO ?= default

.PHONY: help sync lint ansible-lint yamllint molecule

help:
	@echo "Available targets:"
	@echo "  make sync                      # install/update .venv with uv"
	@echo "  make lint                      # run ansible-lint + yamllint"
	@echo "  make ansible-lint              # run ansible-lint"
	@echo "  make yamllint                  # run yamllint"
	@echo "  make molecule SCENARIO=<name>  # run molecule test for a scenario"

sync:
	uv sync

lint: ansible-lint yamllint

ansible-lint:
	uv run ansible-lint .

yamllint:
	uv run yamllint .

molecule:
	uv run molecule test -s $(SCENARIO)
