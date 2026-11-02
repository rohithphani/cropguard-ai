# Cloud SQL for PostgreSQL 16, private IP only (Milestone 4).
# google_sql_database_instance.cropguard_db, google_sql_database.cropguard and
# google_service_networking_connection.private_vpc were imported; their blocks
# were generated from the live resources and live in this file after review.
#
# NOT managed: the database user's password (google_sql_user) - it is stored only
# in Secret Manager (database-url) and must never land in Terraform state.

resource "google_service_networking_connection" "private_vpc" {
  network                 = "projects/${var.project_id}/global/networks/default"
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services_range.name]

  lifecycle { prevent_destroy = true }
}

resource "google_sql_database_instance" "cropguard_db" {
  name                = "cropguard-db"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = true

  settings {
    tier                         = "db-f1-micro"
    edition                      = "ENTERPRISE"
    availability_type            = "ZONAL"
    activation_policy            = "ALWAYS"
    disk_type                    = "PD_SSD"
    disk_size                    = 10
    disk_autoresize              = true
    disk_autoresize_limit        = 0
    pricing_plan                 = "PER_USE"
    connector_enforcement        = "NOT_REQUIRED"
    deletion_protection_enabled  = false
    retain_backups_on_delete     = false
    enable_dataplex_integration  = true
    enable_google_ml_integration = false

    ip_configuration {
      ipv4_enabled                                  = false # no public IP
      private_network                               = "projects/${var.project_id}/global/networks/default"
      enable_private_path_for_google_cloud_services = false
      server_ca_mode                                = "GOOGLE_MANAGED_INTERNAL_CA"
      ssl_mode                                      = "ALLOW_UNENCRYPTED_AND_ENCRYPTED"
    }

    location_preference {
      zone = "${var.region}-a"
    }

    backup_configuration {
      enabled                        = false
      start_time                     = "17:00"
      point_in_time_recovery_enabled = false
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
    # The team stops the instance between work sessions to save cost
    # (activation policy NEVER <-> ALWAYS); that is operational, not drift.
    ignore_changes = [settings[0].activation_policy]
  }

  depends_on = [google_service_networking_connection.private_vpc]
}

resource "google_sql_database" "cropguard" {
  name     = "cropguard"
  instance = google_sql_database_instance.cropguard_db.name
}
