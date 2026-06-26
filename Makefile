# Convenience targets. On Windows without `make`, run the docker commands directly
# (see README.md "Windows / PowerShell" section).

# Set your Docker Hub username:  make push DOCKERHUB_USER=yourname
DOCKERHUB_USER ?= yourname
IMAGE          := $(DOCKERHUB_USER)/insightflow-ai:latest

.PHONY: build up down logs ps seed push pull restart

build:        ## Build the application image
	docker compose --env-file backend/.env build

up:           ## Start the whole stack in the background
	docker compose --env-file backend/.env up -d

down:         ## Stop and remove containers
	docker compose --env-file backend/.env down

restart:
	docker compose --env-file backend/.env restart api worker-website worker-file worker-ai consumer

logs:         ## Tail logs for all services
	docker compose --env-file backend/.env logs -f

ps:
	docker compose --env-file backend/.env ps

seed:         ## Seed 100 users + sample websites/files
	docker compose --env-file backend/.env exec api python -m scripts.seed

# --- Docker Hub ---
push:         ## Build and push image to Docker Hub
	docker build -t $(IMAGE) backend
	docker push $(IMAGE)

pull:
	docker pull $(IMAGE)
