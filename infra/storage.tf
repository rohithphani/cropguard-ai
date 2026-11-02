# Private bucket for uploaded leaf photos (Milestone 4).
resource "google_storage_bucket" "uploads" {
  name                        = "${var.project_id}-uploads"
  location                    = "US-CENTRAL1"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  lifecycle { prevent_destroy = true }
}

resource "google_storage_bucket_iam_member" "uploads_app" {
  bucket = google_storage_bucket.uploads.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app.email}"
}

# Build artifacts too large for git (the 185 MB trained model). The CI
# pipeline downloads them before `docker build`.
resource "google_storage_bucket" "artifacts" {
  name                        = "${var.project_id}-artifacts"
  location                    = "US-CENTRAL1"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  versioning { enabled = true }
}

resource "google_storage_bucket_iam_member" "artifacts_deployer" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.deployer.email}"
}
