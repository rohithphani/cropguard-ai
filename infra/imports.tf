# Resources created by hand in Milestones 2-5, adopted into Terraform state.
# (Import blocks are idempotent: once imported they are no-ops.)

locals {
  pid    = var.project_id
  app_sa = "cropguard-app-sa@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_compute_global_address.private_services_range
  id = "projects/${local.pid}/global/addresses/google-managed-services-default"
}

import {
  to = google_compute_global_address.cropguard_ip
  id = "projects/${local.pid}/global/addresses/cropguard-ip"
}

import {
  to = google_service_networking_connection.private_vpc
  id = "projects/${local.pid}/global/networks/default:servicenetworking.googleapis.com"
}

import {
  to = google_sql_database_instance.cropguard_db
  id = "projects/${local.pid}/instances/cropguard-db"
}

import {
  to = google_sql_database.cropguard
  id = "projects/${local.pid}/instances/cropguard-db/databases/cropguard"
}

import {
  to = google_container_cluster.cropguard
  id = "projects/${local.pid}/locations/${var.region}/clusters/cropguard-cluster"
}

import {
  to = google_storage_bucket.uploads
  id = "${local.pid}-uploads"
}

import {
  to = google_storage_bucket_iam_member.uploads_app
  id = "b/${local.pid}-uploads roles/storage.objectAdmin serviceAccount:${local.app_sa}"
}

import {
  to = google_artifact_registry_repository.cropguard
  id = "projects/${local.pid}/locations/${var.region}/repositories/cropguard"
}

import {
  for_each = toset(local.secret_ids)
  to       = google_secret_manager_secret.app[each.value]
  id       = "projects/${local.pid}/secrets/${each.value}"
}

import {
  to = google_service_account.app
  id = "projects/${local.pid}/serviceAccounts/${local.app_sa}"
}

import {
  for_each = toset(["roles/secretmanager.secretAccessor", "roles/cloudsql.client", "roles/logging.logWriter"])
  to       = google_project_iam_member.app_roles[each.value]
  id       = "${local.pid} ${each.value} serviceAccount:${local.app_sa}"
}

import {
  to = google_service_account_iam_member.app_workload_identity
  id = "projects/${local.pid}/serviceAccounts/${local.app_sa} roles/iam.workloadIdentityUser serviceAccount:${local.pid}.svc.id.goog[default/cropguard-ksa]"
}
