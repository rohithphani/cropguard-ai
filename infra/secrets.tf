# Secret Manager containers only. Secret VALUES are added out-of-band with
# `gcloud secrets versions add` so they never appear in code or Terraform state.
locals {
  secret_ids = ["database-url", "gemini-api-key", "flask-secret-key", "cropguard-api-key", "admin-password"]
}

resource "google_secret_manager_secret" "app" {
  for_each  = toset(local.secret_ids)
  secret_id = each.value
  replication {
    auto {}
  }
}
