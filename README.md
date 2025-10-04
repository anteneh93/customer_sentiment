# Customer Sentiment Analysis Pipeline

A production-ready, real-time feedback processing pipeline built on Google Cloud Platform with AI-powered sentiment analysis using Vertex AI Gemini.

## Architecture Overview

This system processes customer feedback in real-time through the following components:

1. **Feedback Producer** - FastAPI REST service that accepts feedback and publishes to Pub/Sub
2. **AI-Powered Consumer** - Processes messages from Pub/Sub, stores raw data in Spanner, enriches with AI analysis, and stores results in BigQuery
3. **Infrastructure** - GKE cluster, Pub/Sub, Cloud Spanner, BigQuery, and Vertex AI
4. **CI/CD** - GitHub Actions workflow for automated testing, building, and deployment

## System Architecture


```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Customer      │    │   FastAPI       │    │   Pub/Sub       │
│   Feedback      │───▶│   Producer      │───▶│   Topic         │
│   (REST API)    │    │   (Port 8080)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   BigQuery      │◀───│   AI Consumer   │◀───│   Pub/Sub       │
│   (Analytics)   │    │   (Vertex AI)   │    │   Subscription  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Cloud Spanner │
                       │   (Raw Data)    │
                       └─────────────────┘
```

## Features

- **Real-time Processing**: Pub/Sub for scalable message processing
- **AI-Powered Analysis**: Vertex AI Gemini for sentiment analysis and topic extraction
- **Scalable Storage**: Cloud Spanner for raw data, BigQuery for analytics
- **Containerized Deployment**: GKE with auto-scaling
- **Production Ready**: Comprehensive testing, monitoring, and security
- **Infrastructure as Code**: Terraform for reproducible deployments

## AI Analysis

The system uses Vertex AI Gemini to analyze feedback and extract:

- **Sentiment**: POSITIVE, NEGATIVE, or NEUTRAL
- **Topics**: Up to 3 from BILLING, UI_UX, PERFORMANCE, FEATURE_REQUEST

### Example Analysis

**Input:**
```json
{
  "feedback_id": "fdbk-9a8b7c6d",
  "user_id": "user-789",
  "timestamp": "2025-09-29T13:00:00Z",
  "comment": "The new dashboard is visually appealing, but it's incredibly slow to load the main widgets. Also, I think there's an issue with how my latest invoice is calculated in the billing section."
}
```

**AI Output:**
```json
{
  "sentiment": "NEGATIVE",
  "topics": ["PERFORMANCE", "BILLING"]
}
```

## Project Structure

```
customer_sentiment/
├── producer/                 # FastAPI feedback producer
│   ├── app.py              # Main application
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Container definition
│   └── tests/              # Unit tests
├── pipeline/               # AI-powered consumer
│   ├── consumer.py         # Main consumer logic
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Container definition
│   └── tests/              # Unit tests
├── k8s/                    # Kubernetes manifests
│   ├── deployment.yaml     # GKE deployments
│   └── service.yaml       # Services and configs
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # Main infrastructure
│   ├── variables.tf       # Input variables
│   ├── outputs.tf         # Output values
│   └── terraform.tfvars.example
├── .github/workflows/      # CI/CD pipeline
│   └── deploy.yml         # GitHub Actions workflow
└── README.md              # This file
```

## Prerequisites

- Google Cloud Platform account with billing enabled
- `gcloud` CLI installed and configured
- `kubectl` installed
- `terraform` installed (version >= 1.0)
- Docker installed
- Python 3.11+ (recommended) or Python 3.8-3.12

### Python Compatibility

**Recommended**: Python 3.11 (used in Docker containers)
- All Docker containers use Python 3.11 for maximum compatibility
- Avoids Python 3.13 compatibility issues with pydantic-core compilation
- Provides stable runtime environment

**Local Development**: Python 3.8-3.12
- Python 3.13 has compatibility issues with pydantic-core compilation
- Use Python 3.11 or 3.12 for local development
- Docker containers bypass all Python version compatibility issues

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd customer_sentiment
```

### 2. Configure GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable spanner.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 3. Deploy Infrastructure

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan -var="project_id=$PROJECT_ID"
terraform apply -var="project_id=$PROJECT_ID"
```

### 4. Deploy Applications

```bash
# Build and push images
cd ../producer
docker build -t gcr.io/$PROJECT_ID/feedback-producer:latest .
docker push gcr.io/$PROJECT_ID/feedback-producer:latest

cd ../pipeline
docker build -t gcr.io/$PROJECT_ID/feedback-consumer:latest .
docker push gcr.io/$PROJECT_ID/feedback-consumer:latest

# Deploy to GKE
gcloud container clusters get-credentials feedback-cluster --zone us-central1-a
kubectl apply -f ../k8s/service.yaml
kubectl apply -f ../k8s/deployment.yaml
```

### 5. Test the System

```bash
# Get the producer service endpoint
kubectl get service feedback-producer-service -n feedback-system

# Submit test feedback
curl -X POST "http://<EXTERNAL-IP>/v1/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "comment": "The new dashboard is visually appealing, but it is incredibly slow to load the main widgets."
  }'
```

## Development

### Running Tests

```bash
# Test producer
cd producer
pip3 install -r requirements.txt
python3 -m pytest tests/ -v

# Test consumer
cd ../pipeline
pip3 install -r requirements.txt
python3 -m pytest tests/ -v
```

### Local Development

#### Option 1: Docker (Recommended)
```bash
# Run producer with Docker
cd producer
docker build -t feedback-producer .
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT="your-project-id" \
  -e PUBSUB_TOPIC="customer-feedback" \
  -v ~/.config/gcloud/application_default_credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  feedback-producer

# Run consumer with Docker
cd pipeline
docker build -t feedback-consumer .
docker run \
  -e GOOGLE_CLOUD_PROJECT="your-project-id" \
  -e PUBSUB_SUBSCRIPTION="customer-feedback-sub" \
  -v ~/.config/gcloud/application_default_credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  feedback-consumer
```

#### Option 2: Local Python (Python 3.8-3.12)
```bash
# Run producer locally (requires Python 3.8-3.12)
cd producer
export GOOGLE_CLOUD_PROJECT="your-project-id"
export PUBSUB_TOPIC="customer-feedback"
python3 app.py

# Run consumer locally (requires Python 3.8-3.12)
cd pipeline
export GOOGLE_CLOUD_PROJECT="your-project-id"
export PUBSUB_SUBSCRIPTION="customer-feedback-sub"
# ... other environment variables
python3 consumer.py
```

**Note**: Docker approach is recommended to avoid Python version compatibility issues.

### Python Compatibility Solutions

#### Problem: Python 3.13 Compatibility Issues
- **pydantic-core compilation failures** due to Rust dependencies
- **cgi module removal** in Python 3.13
- **ForwardRef._evaluate() API changes** breaking Pydantic

#### Solutions Implemented:

1. **Docker Containers (Recommended)**:
   - All containers use Python 3.11 for maximum compatibility
   - Bypasses all Python version compatibility issues
   - Provides consistent runtime environment

2. **Version Pinning**:
   - Updated requirements.txt with compatible package versions
   - FastAPI 0.100.0, Pydantic 2.3.0, Google Cloud libraries 2.15.0
   - Compatible with Python 3.8-3.12

3. **Alternative Installation Methods**:
   ```bash
   # Use pre-compiled wheels
   pip3 install --only-binary=all -r requirements.txt
   
   # Or install Rust for compilation
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source ~/.cargo/env
   pip3 install -r requirements.txt
   ```

## Configuration

### Environment Variables

**Producer:**
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `PUBSUB_TOPIC`: Pub/Sub topic name
- `PORT`: Service port (default: 8080)

**Consumer:**
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `PUBSUB_SUBSCRIPTION`: Pub/Sub subscription name
- `SPANNER_INSTANCE_ID`: Spanner instance ID
- `SPANNER_DATABASE_ID`: Spanner database ID
- `BIGQUERY_DATASET_ID`: BigQuery dataset ID
- `BIGQUERY_TABLE_ID`: BigQuery table ID
- `VERTEXAI_LOCATION`: Vertex AI region

### Terraform Variables

See `terraform/terraform.tfvars.example` for all configurable options.

## Monitoring and Observability

### Health Checks

- **Producer**: `GET /health` endpoint
- **Consumer**: Built-in health checks in Kubernetes

### Logging

All services use structured logging with appropriate log levels.

### Metrics

- Pub/Sub message throughput
- Spanner write operations
- BigQuery insert operations
- Vertex AI API calls

## Security

- Workload Identity for service-to-service authentication
- Least privilege IAM roles
- Private GKE cluster
- Container security scanning
- Non-root containers

## Scaling

- **Producer**: Horizontal pod autoscaling based on CPU/memory
- **Consumer**: Horizontal pod autoscaling based on Pub/Sub backlog
- **Infrastructure**: Auto-scaling node pools

## Cost Optimization

- Preemptible nodes for non-critical workloads
- Appropriate machine types for each service
- Efficient resource requests and limits
- Pub/Sub message retention policies

## Troubleshooting

### Common Issues

1. **Python 3.13 Compatibility Issues**: 
   - **Error**: `pydantic-core` compilation failures
   - **Solution**: Use Docker containers (Python 3.11) or downgrade to Python 3.11/3.12
   - **Alternative**: Use `pip3 install --only-binary=all` for pre-compiled wheels

2. **Authentication Errors**: Ensure service accounts have proper IAM roles
3. **Pub/Sub Issues**: Check topic and subscription exist
4. **Spanner Errors**: Verify instance and database exist
5. **BigQuery Issues**: Check dataset and table permissions
6. **Vertex AI Errors**: Ensure Vertex AI API is enabled
7. **GCP Quota Issues**: Request quota increases for SSD, Spanner, and GKE resources

### Debugging

```bash
# Check pod logs
kubectl logs -f deployment/feedback-producer -n feedback-system
kubectl logs -f deployment/feedback-consumer -n feedback-system

# Check service status
kubectl get pods -n feedback-system
kubectl get services -n feedback-system
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Open an issue on GitHub
4. Contact the development team
