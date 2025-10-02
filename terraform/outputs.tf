output "cluster_name" {
  description = "The name of the GKE cluster"
  value       = google_container_cluster.feedback_cluster.name
}

output "cluster_endpoint" {
  description = "The endpoint of the GKE cluster"
  value       = google_container_cluster.feedback_cluster.endpoint
}

output "cluster_ca_certificate" {
  description = "The CA certificate of the GKE cluster"
  value       = google_container_cluster.feedback_cluster.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "pubsub_topic_name" {
  description = "The name of the Pub/Sub topic"
  value       = google_pubsub_topic.customer_feedback.name
}

output "pubsub_subscription_name" {
  description = "The name of the Pub/Sub subscription"
  value       = google_pubsub_subscription.customer_feedback_sub.name
}

output "spanner_instance_name" {
  description = "The name of the Spanner instance"
  value       = google_spanner_instance.feedback_instance.name
}

output "spanner_database_name" {
  description = "The name of the Spanner database"
  value       = google_spanner_database.feedback_database.name
}

output "bigquery_dataset_id" {
  description = "The ID of the BigQuery dataset"
  value       = google_bigquery_dataset.feedback_analysis.dataset_id
}

output "bigquery_table_id" {
  description = "The ID of the BigQuery table"
  value       = google_bigquery_table.feedback_analysis.table_id
}

output "artifact_registry_repository" {
  description = "The name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.feedback_repo.name
}

output "producer_service_account_email" {
  description = "The email of the producer service account"
  value       = google_service_account.feedback_producer.email
}

output "consumer_service_account_email" {
  description = "The email of the consumer service account"
  value       = google_service_account.feedback_consumer.email
}
