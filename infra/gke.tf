# GKE Autopilot cluster (Milestone 5). Imported; block generated from the live
# cluster after review. Kubernetes objects inside it (Deployment, Service,
# Ingress, HPA, PDB, ManagedCertificate) are managed by kubectl / the CI
# pipeline from the k8s/ folder, not by Terraform.

resource "google_container_cluster" "cropguard" {
  name                = "cropguard-cluster"
  location            = var.region
  enable_autopilot    = true
  network             = "projects/${var.project_id}/global/networks/default"
  subnetwork          = "projects/${var.project_id}/regions/${var.region}/subnetworks/default"
  deletion_protection = true

  release_channel {
    channel = "REGULAR"
  }

  # Workload Identity: pods use Google service accounts, no key files.
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"] # container stdout -> Cloud Logging
  }

  lifecycle {
    prevent_destroy = true
    # Autopilot manages these itself (auto-upgrades, node provisioning).
    ignore_changes = [node_version, min_master_version]
  }
}
