# Configure the Google Cloud Provider
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "container.googleapis.com",
    "pubsub.googleapis.com",
    "spanner.googleapis.com",
    "bigquery.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com"
  ])
  
  service = each.value
  disable_on_destroy = false
}

# Create GKE cluster
resource "google_container_cluster" "feedback_cluster" {
  name     = var.cluster_name
  location = var.region
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Enable network policy
  network_policy {
    enabled = true
  }
  
  # Enable network policy addon
  addons_config {
    network_policy_config {
      disabled = false
    }
  }
  
  # Enable private cluster
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }
  
  # Enable IP aliasing
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  
  # Enable network policy
  network    = google_compute_network.feedback_vpc.name
  subnetwork = google_compute_subnetwork.feedback_subnet.name
  
  depends_on = [
    google_project_service.required_apis,
    google_compute_network.feedback_vpc,
    google_compute_subnetwork.feedback_subnet
  ]
}

# Create node pool
resource "google_container_node_pool" "feedback_nodes" {
  name       = "${var.cluster_name}-node-pool"
  location   = var.region
  cluster    = google_container_cluster.feedback_cluster.name
  node_count = var.node_count
  
  node_config {
    preemptible  = var.preemptible_nodes
    machine_type = var.machine_type
    
    # Enable Workload Identity
    service_account = google_service_account.feedback_consumer.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    # Enable GKE metadata server
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Enable network policy
    tags = ["gke-node", "feedback-system"]
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }
}

# Create VPC network
resource "google_compute_network" "feedback_vpc" {
  name                    = "feedback-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Create subnet
resource "google_compute_subnetwork" "feedback_subnet" {
  name          = "feedback-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.feedback_vpc.id
  
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/20"
  }
}

# Create firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "feedback-allow-internal"
  network = google_compute_network.feedback_vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = ["10.0.0.0/8"]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "feedback-allow-ssh"
  network = google_compute_network.feedback_vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node"]
}

# Create Pub/Sub topic
resource "google_pubsub_topic" "customer_feedback" {
  name = var.pubsub_topic_name
  
  depends_on = [google_project_service.required_apis]
}

# Create Pub/Sub subscription
resource "google_pubsub_subscription" "customer_feedback_sub" {
  name  = var.pubsub_subscription_name
  topic = google_pubsub_topic.customer_feedback.name
  
  # Configure message retention
  message_retention_duration = "600s"
  
  # Configure acknowledgment deadline
  ack_deadline_seconds = 60
  
  # Enable exactly-once delivery
  enable_exactly_once_delivery = true
  
  # Configure retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Create Cloud Spanner instance
resource "google_spanner_instance" "feedback_instance" {
  config         = "regional-${var.region}"
  display_name   = "Feedback Instance"
  processing_units = 100
  
  depends_on = [google_project_service.required_apis]
}

# Create Cloud Spanner database
resource "google_spanner_database" "feedback_database" {
  instance = google_spanner_instance.feedback_instance.name
  name     = var.spanner_database_name
  
  ddl = [
    "CREATE TABLE raw_feedback (",
    "  feedback_id STRING(36) NOT NULL,",
    "  user_id STRING(36) NOT NULL,",
    "  timestamp STRING(50) NOT NULL,",
    "  comment STRING(MAX) NOT NULL,",
    "  created_at STRING(50) NOT NULL",
    ") PRIMARY KEY (feedback_id)"
  ]
  
  deletion_protection = false
}

# Create BigQuery dataset
resource "google_bigquery_dataset" "feedback_analysis" {
  dataset_id = var.bigquery_dataset_id
  location   = var.region
  
  depends_on = [google_project_service.required_apis]
}

# Create BigQuery table
resource "google_bigquery_table" "feedback_analysis" {
  dataset_id = google_bigquery_dataset.feedback_analysis.dataset_id
  table_id   = var.bigquery_table_id
  
  schema = jsonencode([
    {
      name = "feedback_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "sentiment"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "topics"
      type = "STRING"
      mode = "REPEATED"
    },
    {
      name = "timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    }
  ])
  
  time_partitioning {
    type = "DAY"
    field = "timestamp"
  }
  
  deletion_protection = false
}

# Create Artifact Registry repository
resource "google_artifact_registry_repository" "feedback_repo" {
  location      = var.region
  repository_id = "feedback-repo"
  description   = "Docker repository for feedback system"
  format        = "DOCKER"
  
  depends_on = [google_project_service.required_apis]
}

# Create service accounts
resource "google_service_account" "feedback_producer" {
  account_id   = "feedback-producer"
  display_name = "Feedback Producer Service Account"
  description  = "Service account for feedback producer service"
}

resource "google_service_account" "feedback_consumer" {
  account_id   = "feedback-consumer"
  display_name = "Feedback Consumer Service Account"
  description  = "Service account for feedback consumer service"
}

# Create IAM bindings for producer
resource "google_project_iam_member" "producer_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.feedback_producer.email}"
}

# Create IAM bindings for consumer
resource "google_project_iam_member" "consumer_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.feedback_consumer.email}"
}

resource "google_project_iam_member" "consumer_spanner_user" {
  project = var.project_id
  role    = "roles/spanner.databaseUser"
  member  = "serviceAccount:${google_service_account.feedback_consumer.email}"
}

resource "google_project_iam_member" "consumer_bigquery_user" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.feedback_consumer.email}"
}

resource "google_project_iam_member" "consumer_vertexai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.feedback_consumer.email}"
}

# Enable Workload Identity binding for consumer
resource "google_service_account_iam_member" "consumer_workload_identity" {
  service_account_id = google_service_account.feedback_consumer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[feedback-system/feedback-consumer-sa]"
}

# Enable Workload Identity binding for producer
resource "google_service_account_iam_member" "producer_workload_identity" {
  service_account_id = google_service_account.feedback_producer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[feedback-system/feedback-producer-sa]"
}
