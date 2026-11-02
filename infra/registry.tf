# Docker images (Milestone 3). CI pushes one tag per commit SHA.
resource "google_artifact_registry_repository" "cropguard" {
  location      = var.region
  repository_id = "cropguard"
  format        = "DOCKER"
  description   = "CropGuard AI container images"
}

resource "google_artifact_registry_repository_iam_member" "deployer_writer" {
  location   = google_artifact_registry_repository.cropguard.location
  repository = google_artifact_registry_repository.cropguard.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}
