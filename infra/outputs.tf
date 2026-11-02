output "app_url" {
  value = var.app_url
}

output "static_ip" {
  value = google_compute_global_address.cropguard_ip.address
}

output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.cropguard.repository_id}/cropguard-app"
}

output "github_wif_provider" {
  description = "Used by .github/workflows/deploy.yml (google-github-actions/auth)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  value = google_service_account.deployer.email
}

output "http_5xx_metric" {
  value = "logging.googleapis.com/user/${google_logging_metric.http_5xx.name}"
}
