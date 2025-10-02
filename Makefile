# Customer Sentiment Analysis Pipeline Makefile

.PHONY: help build test deploy clean setup

# Default target
help:
	@echo "Available targets:"
	@echo "  setup     - Setup development environment"
	@echo "  test      - Run all tests"
	@echo "  build     - Build Docker images"
	@echo "  deploy    - Deploy to GKE"
	@echo "  clean     - Clean up resources"
	@echo "  producer  - Run producer locally"
	@echo "  consumer  - Run consumer locally"

# Variables
PROJECT_ID ?= $(shell gcloud config get-value project)
REGION ?= us-central1
CLUSTER_NAME ?= feedback-cluster
ZONE ?= us-central1-a

# Setup development environment
setup:
	@echo "Setting up development environment..."
	pip install -r producer/requirements.txt
	pip install -r pipeline/requirements.txt
	@echo "Setup complete!"

# Run tests
test:
	@echo "Running producer tests..."
	cd producer && python -m pytest tests/ -v
	@echo "Running pipeline tests..."
	cd pipeline && python -m pytest tests/ -v

# Build Docker images
build:
	@echo "Building producer image..."
	docker build -t gcr.io/$(PROJECT_ID)/feedback-producer:latest ./producer
	@echo "Building consumer image..."
	docker build -t gcr.io/$(PROJECT_ID)/feedback-consumer:latest ./pipeline

# Push Docker images
push: build
	@echo "Pushing images to GCR..."
	docker push gcr.io/$(PROJECT_ID)/feedback-producer:latest
	docker push gcr.io/$(PROJECT_ID)/feedback-consumer:latest

# Deploy infrastructure with Terraform
terraform-init:
	cd terraform && terraform init

terraform-plan:
	cd terraform && terraform plan -var="project_id=$(PROJECT_ID)"

terraform-apply:
	cd terraform && terraform apply -var="project_id=$(PROJECT_ID)"

# Deploy to GKE
deploy: push
	@echo "Deploying to GKE..."
	gcloud container clusters get-credentials $(CLUSTER_NAME) --zone $(ZONE)
	kubectl apply -f k8s/service.yaml
	kubectl apply -f k8s/deployment.yaml
	@echo "Deployment complete!"

# Run producer locally
producer:
	@echo "Starting producer locally..."
	cd producer && python app.py

# Run consumer locally
consumer:
	@echo "Starting consumer locally..."
	cd pipeline && python consumer.py

# Clean up resources
clean:
	@echo "Cleaning up resources..."
	kubectl delete namespace feedback-system --ignore-not-found=true
	cd terraform && terraform destroy -var="project_id=$(PROJECT_ID)" -auto-approve

# Get service endpoints
status:
	@echo "Getting service status..."
	kubectl get pods -n feedback-system
	kubectl get services -n feedback-system

# Test the system
test-system:
	@echo "Testing the system..."
	@SERVICE_IP=$$(kubectl get service feedback-producer-service -n feedback-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}'); \
	if [ -z "$$SERVICE_IP" ]; then \
		echo "Service not ready yet. Run 'make status' to check."; \
	else \
		echo "Testing producer endpoint at http://$$SERVICE_IP/v1/feedback"; \
		curl -X POST "http://$$SERVICE_IP/v1/feedback" \
			-H "Content-Type: application/json" \
			-d '{"user_id": "test-user", "comment": "This is a test feedback message."}'; \
	fi

# Full deployment pipeline
deploy-all: terraform-init terraform-apply deploy
	@echo "Full deployment complete!"

# Development workflow
dev: setup test
	@echo "Development setup complete!"
