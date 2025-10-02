variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "cluster_name" {
  description = "The name of the GKE cluster"
  type        = string
  default     = "feedback-cluster"
}

variable "node_count" {
  description = "The number of nodes in the GKE cluster"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "The machine type for GKE nodes"
  type        = string
  default     = "e2-medium"
}

variable "preemptible_nodes" {
  description = "Whether to use preemptible nodes"
  type        = bool
  default     = false
}

variable "pubsub_topic_name" {
  description = "The name of the Pub/Sub topic"
  type        = string
  default     = "customer-feedback"
}

variable "pubsub_subscription_name" {
  description = "The name of the Pub/Sub subscription"
  type        = string
  default     = "customer-feedback-sub"
}

variable "spanner_database_name" {
  description = "The name of the Spanner database"
  type        = string
  default     = "feedback-db"
}

variable "bigquery_dataset_id" {
  description = "The ID of the BigQuery dataset"
  type        = string
  default     = "feedback_analysis"
}

variable "bigquery_table_id" {
  description = "The ID of the BigQuery table"
  type        = string
  default     = "feedback_analysis"
}
