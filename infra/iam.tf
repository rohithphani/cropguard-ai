# Runtime identity of the app pods (Workload Identity: KSA default/cropguard-ksa
# acts as this Google service account; no key files anywhere).
resource "google_service_account" "app" {
  account_id   = "cropguard-app-sa"
  display_name = "CropGuard GKE app"
}

resource "google_project_iam_member" "app_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/logging.logWriter",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app.email}"
}

resource "google_service_account_iam_member" "app_workload_identity" {
  service_account_id = google_service_account.app.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/cropguard-ksa]"
}
