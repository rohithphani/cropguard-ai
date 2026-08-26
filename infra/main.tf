terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ─── Networking: private services access for Cloud SQL (Step 6) ──────────────

resource "google_compute_global_address" "private_services_range" {
  name          = "google-managed-services-default"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = "projects/${var.project_id}/global/networks/default"
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = "projects/${var.project_id}/global/networks/default"
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services_range.name]
}

# ─── Cloud SQL — private IP only, no public endpoint (Step 6) ────────────────

resource "google_sql_database_instance" "cropguard_db" {
  name                = "cropguard-db"
  database_version    = "POSTGRES_15"
  region              = var.region
  deletion_protection = false # allows terraform destroy in Step 12.3

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled    = false
      private_network = "projects/${var.project_id}/global/networks/default"
    }
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

# ─── GCS bucket for uploaded leaf images (Step 7) ─────────────────────────────

resource "google_storage_bucket" "uploads" {
  name                        = "cropguard-uploads-${var.project_suffix}"
  location                    = var.region
  uniform_bucket_level_access = true
}

# ─── Artifact Registry for the Docker images (Step 5) ─────────────────────────

resource "google_artifact_registry_repository" "repo" {
  repository_id = "cropguard-repo"
  format        = "DOCKER"
  location      = var.region
}

# ─── GKE Autopilot cluster (Step 9) ────────────────────────────────────────────

resource "google_container_cluster" "cluster" {
  name                = "cropguard-cluster"
  location            = var.region
  enable_autopilot    = true
  deletion_protection = false
}

# ─── Secret Manager — containers only, never the values (Step 8) ──────────────
# Real secret VALUES were added once via `gcloud secrets versions add` and are
# never stored in Terraform state or source control. Re-applying this file
# will never overwrite real secret data — it only manages the empty container.

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "flask_secret_key" {
  secret_id = "flask-secret-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "cropguard_api_key" {
  secret_id = "cropguard-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  replication {
    auto {}
  }
}

# ─── IAM: the app's runtime identity (default compute SA) can read secrets ────
# Same identity reused across the VM (Step 8) and GKE via Workload Identity
# (Step 9) — no downloaded key files anywhere.

locals {
  runtime_sa = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "gemini_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.runtime_sa
}

resource "google_secret_manager_secret_iam_member" "flask_secret_access" {
  secret_id = google_secret_manager_secret.flask_secret_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.runtime_sa
}

resource "google_secret_manager_secret_iam_member" "api_key_access" {
  secret_id = google_secret_manager_secret.cropguard_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.runtime_sa
}

resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.runtime_sa
}

# ─── IAM: bucket access for uploads (Step 7) ───────────────────────────────────

resource "google_storage_bucket_iam_member" "uploads_access" {
  bucket = google_storage_bucket.uploads.name
  role   = "roles/storage.objectAdmin"
  member = local.runtime_sa
}

# ─── Workload Identity: KSA <-> compute default SA, no key files (Step 9) ─────

resource "google_service_account_iam_member" "workload_identity_binding" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.project_number}-compute@developer.gserviceaccount.com"
  role                = "roles/iam.workloadIdentityUser"
  member              = "serviceAccount:${var.project_id}.svc.id.goog[default/cropguard-app-ksa]"
}

# ─── Global static IP for the Ingress (Step 10) ────────────────────────────────

resource "google_compute_global_address" "cropguard_ip" {
  name = "cropguard-ip"
}

# ─── Billing budget with 20/50/100% alerts (Step 2) ────────────────────────────

resource "google_billing_budget" "budget" {
  billing_account = var.billing_account
  display_name    = "cropguard-budget"

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "50"
    }
  }

  threshold_rules { threshold_percent = 0.2 }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 1.0 }
}
