# CropGuard AI - infrastructure as code (Milestone 6)
#
# Everything here already existed (built by hand in Milestones 2-5) and was
# brought under Terraform with `import` blocks (imports.tf); the monitoring,
# CI/CD identity and artifact bucket were created by Terraform.
# State lives in a GCS bucket (never in git). See README.md for coverage and
# the resources intentionally NOT managed here.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0, < 8.0"
    }
  }
  backend "gcs" {
    bucket = "cropguard-ai-509423-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# APIs the platform depends on. disable_on_destroy = false: a `terraform destroy`
# must never switch off an API that other resources still use.
locals {
  services = [
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "servicenetworking.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}
