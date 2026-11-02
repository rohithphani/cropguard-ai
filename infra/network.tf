# Private Services Access: a /16 reserved in the default VPC and peered to
# Google's service network, so Cloud SQL gets a private IP only (Milestone 4).

resource "google_compute_global_address" "private_services_range" {
  name          = "google-managed-services-default"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = "projects/${var.project_id}/global/networks/default"

  lifecycle { prevent_destroy = true }
}

# google_service_networking_connection.private_vpc is generated from the live
# resource (see database.tf / generated.tf) to match it exactly.

# Global static IP used by the GKE Ingress / HTTPS load balancer (Milestone 5).
resource "google_compute_global_address" "cropguard_ip" {
  name = "cropguard-ip"
}
