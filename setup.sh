#!/bin/bash

# Customer Sentiment Analysis Pipeline Setup Script
# This script sets up the development environment and deploys the infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v gcloud &> /dev/null; then
        missing_tools+=("gcloud")
    fi
    
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    if ! command -v terraform &> /dev/null; then
        missing_tools+=("terraform")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_status "Please install the missing tools and run this script again."
        exit 1
    fi
    
    print_success "All prerequisites are installed"
}

# Get project configuration
get_project_config() {
    print_status "Getting project configuration..."
    
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            print_error "No GCP project set. Please run: gcloud config set project YOUR_PROJECT_ID"
            exit 1
        fi
    fi
    
    print_success "Using project: $PROJECT_ID"
}

# Enable required APIs
enable_apis() {
    print_status "Enabling required Google Cloud APIs..."
    
    local apis=(
        "container.googleapis.com"
        "pubsub.googleapis.com"
        "spanner.googleapis.com"
        "bigquery.googleapis.com"
        "aiplatform.googleapis.com"
        "artifactregistry.googleapis.com"
        "cloudbuild.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        print_status "Enabling $api..."
        gcloud services enable "$api" --quiet
    done
    
    print_success "All APIs enabled"
}

# Setup Python environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install -r producer/requirements.txt
    pip install -r pipeline/requirements.txt
    
    print_success "Python environment setup complete"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    source venv/bin/activate
    
    # Test producer
    print_status "Testing producer..."
    cd producer
    python3 -m pytest tests/ -v
    cd ..
    
    # Test pipeline
    print_status "Testing pipeline..."
    cd pipeline
    python3 -m pytest tests/ -v
    cd ..
    
    print_success "All tests passed"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Create terraform.tfvars if it doesn't exist
    if [ ! -f "terraform.tfvars" ]; then
        cp terraform.tfvars.example terraform.tfvars
        print_warning "Created terraform.tfvars from example. Please review and update if needed."
    fi
    
    # Plan and apply
    terraform plan -var="project_id=$PROJECT_ID"
    terraform apply -var="project_id=$PROJECT_ID" -auto-approve
    
    cd ..
    
    print_success "Infrastructure deployed"
}

# Build and push Docker images
build_and_push_images() {
    print_status "Building and pushing Docker images..."
    
    # Configure Docker for GCR
    gcloud auth configure-docker --quiet
    
    # Build and push producer
    print_status "Building producer image..."
    docker build -t "gcr.io/$PROJECT_ID/feedback-producer:latest" ./producer
    docker push "gcr.io/$PROJECT_ID/feedback-producer:latest"
    
    # Build and push consumer
    print_status "Building consumer image..."
    docker build -t "gcr.io/$PROJECT_ID/feedback-consumer:latest" ./pipeline
    docker push "gcr.io/$PROJECT_ID/feedback-consumer:latest"
    
    print_success "Images built and pushed"
}

# Deploy to GKE
deploy_to_gke() {
    print_status "Deploying to GKE..."
    
    # Get cluster credentials
    gcloud container clusters get-credentials feedback-cluster --zone us-central1-a
    
    # Update Kubernetes manifests with project ID
    sed -i.bak "s/your-gcp-project-id/$PROJECT_ID/g" k8s/service.yaml
    sed -i.bak "s/gcr.io\/PROJECT_ID/gcr.io\/$PROJECT_ID/g" k8s/deployment.yaml
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/deployment.yaml
    
    # Wait for deployments
    print_status "Waiting for deployments to be ready..."
    kubectl rollout status deployment/feedback-producer -n feedback-system --timeout=300s
    kubectl rollout status deployment/feedback-consumer -n feedback-system --timeout=300s
    
    print_success "Deployed to GKE"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Get service endpoint
    SERVICE_IP=$(kubectl get service feedback-producer-service -n feedback-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -z "$SERVICE_IP" ]; then
        print_warning "Service not ready yet. Run 'kubectl get services -n feedback-system' to check status."
        return
    fi
    
    print_status "Testing producer endpoint at http://$SERVICE_IP/v1/feedback"
    
    # Test health endpoint
    if curl -f "http://$SERVICE_IP/health" > /dev/null 2>&1; then
        print_success "Health check passed"
    else
        print_warning "Health check failed"
    fi
    
    # Test feedback submission
    RESPONSE=$(curl -s -X POST "http://$SERVICE_IP/v1/feedback" \
        -H "Content-Type: application/json" \
        -d '{"user_id": "test-user", "comment": "This is a test feedback message for the sentiment analysis pipeline."}')
    
    if echo "$RESPONSE" | grep -q "success.*true"; then
        print_success "Feedback submission test passed"
    else
        print_warning "Feedback submission test failed"
    fi
    
    print_status "Service endpoint: http://$SERVICE_IP"
}

# Show deployment status
show_status() {
    print_status "Deployment Status:"
    echo ""
    
    print_status "Kubernetes Resources:"
    kubectl get pods -n feedback-system
    echo ""
    kubectl get services -n feedback-system
    echo ""
    
    print_status "Terraform Outputs:"
    cd terraform
    terraform output
    cd ..
}

# Cleanup function
cleanup() {
    print_status "Cleaning up resources..."
    
    # Delete Kubernetes resources
    kubectl delete namespace feedback-system --ignore-not-found=true
    
    # Destroy Terraform resources
    cd terraform
    terraform destroy -var="project_id=$PROJECT_ID" -auto-approve
    cd ..
    
    print_success "Cleanup complete"
}

# Main function
main() {
    print_status "Starting Customer Sentiment Analysis Pipeline Setup"
    echo ""
    
    # Parse command line arguments
    case "${1:-setup}" in
        "setup")
            check_prerequisites
            get_project_config
            enable_apis
            setup_python_env
            run_tests
            deploy_infrastructure
            build_and_push_images
            deploy_to_gke
            test_deployment
            show_status
            ;;
        "test")
            check_prerequisites
            setup_python_env
            run_tests
            ;;
        "deploy")
            check_prerequisites
            get_project_config
            build_and_push_images
            deploy_to_gke
            test_deployment
            show_status
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            get_project_config
            cleanup
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [setup|test|deploy|status|cleanup|help]"
            echo ""
            echo "Commands:"
            echo "  setup   - Full setup and deployment (default)"
            echo "  test    - Run tests only"
            echo "  deploy   - Deploy to GKE (assumes infrastructure exists)"
            echo "  status  - Show deployment status"
            echo "  cleanup - Clean up all resources"
            echo "  help    - Show this help message"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    print_success "Setup complete!"
}

# Run main function with all arguments
main "$@"
