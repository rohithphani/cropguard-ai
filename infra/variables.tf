variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_number" {
  description = "GCP project number (used to reference the default compute service account)"
  type        = string
}

variable "project_suffix" {
  description = "Suffix used in globally-unique bucket names (matches the project number suffix used when the bucket was first created)"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "billing_account" {
  description = "Billing account ID, format XXXXXX-XXXXXX-XXXXXX"
  type        = string
}
