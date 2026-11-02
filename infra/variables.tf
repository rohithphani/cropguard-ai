variable "project_id" {
  type    = string
  default = "cropguard-ai-509423"
}

variable "project_number" {
  type    = string
  default = "387386737350"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "github_repo" {
  description = "owner/repo allowed to deploy through Workload Identity Federation"
  type        = string
  default     = "rohithphani/cropguard-ai"
}

variable "alert_email" {
  description = "Inbox that receives Cloud Monitoring alert notifications"
  type        = string
  default     = "rahulreddykesireddy2002@gmail.com"
}

variable "app_url" {
  type    = string
  default = "https://136-68-161-188.sslip.io"
}
