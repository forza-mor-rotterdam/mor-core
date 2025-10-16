# Build scripts to run commands within the Docker container or create local environments

# Docker variables
RUN_IN_NEW_WEBCONTEXT = docker compose run -it core_app
EXEC_IN_WEB = docker compose run core_app
EXEC_IN_WEB_CMD = $(EXEC_IN_WEB) python manage.py

#  General
##############################################

initial_install: create_docker_networks build run

build: ## build the stack
	@echo Building from file. './docker-compose.yml.'
	docker compose build

run: ## start the stack
	@echo Running from file. './docker-compose.yml.'
	docker compose up

run_and_build: ## Build and then start the stack
	@echo Building containers and running from file. './docker-compose.yml.'
	docker compose up --build

run_frontend: ## Run the frontend
	cd app/frontend && \
	npm install && \
	npm run watch

stop: ## Stop containers
	@echo Stopping containers.
	docker compose down

clear_docker_volumes: ## clear docker volumes
	check_clean_db
	@echo Stopping and removing containers.
	docker compose down -v

create_superuser: ## create superuser for public tenant
	@echo Create superuser. You will be prompted for email and password
	$(EXEC_IN_WEB_CMD) createsuperuser

createusers: ## create user for mor-core
	@echo Create user for more-core
	$(EXEC_IN_WEB_CMD) createusers

create_applicaties: ## Create applicaties for more-core
	@echo Creating applicaties
	$(EXEC_IN_WEB_CMD) create_applicaties

create_meldingen: ## Create meldingen for more-core
	@echo Creating meldingen for mor-core
	$(EXEC_IN_WEB_CMD) create_meldingen

check_clean_db: ## clear docker vols
	@echo -n "This will clear local docker volumes before running tests. Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]

format: ## Use pre-commit config to format files
	pre-commit run --all-files

create_docker_networks:
	docker network create mor_network && \
    docker network create mor_bridge_network

# Static files
##############################################

collectstatic: ## collectstatic files
	$(EXEC_IN_WEB_CMD) collectstatic

makemigrations: ## Makemigrations
	$(EXEC_IN_WEB_CMD) makemigrations

migrate: ## Migrate
	$(EXEC_IN_WEB_CMD) migrate

create_app:
	@read -p "Enter the name of the new app: " app_name; \
	mkdir -p app/apps/$$app_name; \
	$(EXEC_IN_WEB_CMD) startapp $$app_name apps/$$app_name


# Tests
##############################################
run_tests:
	$(EXEC_IN_WEB_CMD) test

run_tests_ordered:
	$(EXEC_IN_WEB_CMD) test apps.meldingen.tests.tests_api
	$(EXEC_IN_WEB_CMD) test apps.meldingen.tests.tests_models
