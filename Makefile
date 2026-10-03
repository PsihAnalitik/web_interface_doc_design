SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
SERVER_DIR := $(ROOT_DIR)case-finder-main/server
ENV_FILE ?= $(SERVER_DIR)/.env
ENV_PATH := $(abspath $(ENV_FILE))
COMPOSE = CASE_FINDER_ENV_FILE="$(ENV_PATH)" docker compose --project-directory "$(SERVER_DIR)" --env-file "$(ENV_PATH)" -f "$(SERVER_DIR)/docker-compose.yml" -f "$(ROOT_DIR)compose.web.yaml"

.PHONY: help init check-env up down status logs

help:
	@printf '%s\n' \
	  'make init    — создать .env из примера (существующий файл сохраняется)' \
	  'make up      — собрать и запустить фронтенд, API и worker' \
	  'make down    — остановить сервисы, сохранив данные заданий' \
	  'make status  — показать состояние сервисов' \
	  'make logs    — показать логи (Ctrl+C завершает просмотр)'

init:
	@if [[ -e "$(ENV_PATH)" ]]; then \
	  printf 'Конфигурация уже существует: %s\n' "$(ENV_PATH)"; \
	else \
	  umask 077; \
	  cp "$(SERVER_DIR)/.env.example" "$(ENV_PATH)"; \
	  printf 'Создан %s. Укажите OPENAI_API_KEY и API_USERS перед make up.\n' "$(ENV_PATH)"; \
	fi

check-env:
	@test -f "$(ENV_PATH)" || { printf 'Нет %s. Выполните make init и настройте OPENAI_API_KEY и API_USERS.\n' "$(ENV_PATH)" >&2; exit 1; }

up: check-env
	@$(COMPOSE) up --build --detach --wait --wait-timeout 120
	@address=$$($(COMPOSE) port web 4173); printf 'Сервисы запущены. Интерфейс: http://%s\n' "$$address"

down: check-env
	@$(COMPOSE) down

status: check-env
	@$(COMPOSE) ps

logs: check-env
	@$(COMPOSE) logs --follow --tail=100
