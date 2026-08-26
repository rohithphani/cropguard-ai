output "cloud_sql_connection_name" {
  value = google_sql_database_instance.cropguard_db.connection_name
}

output "uploads_bucket" {
  value = google_storage_bucket.uploads.name
}

output "artifact_registry_repo" {
  value = google_artifact_registry_repository.repo.name
}

output "gke_cluster_name" {
  value = google_container_cluster.cluster.name
}

output "static_ip_address" {
  value = google_compute_global_address.cropguard_ip.address
}
