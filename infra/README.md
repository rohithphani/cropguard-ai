# CropGuard AI - Terraform

State: `gs://cropguard-ai-509423-tfstate` (GCS backend, versioned). State files are git-ignored.

```
terraform init
terraform plan          # refresh is on by default; expected: "No changes."
```

## Managed by Terraform

| Area | Resources |
|---|---|
| APIs | compute, container, sqladmin, servicenetworking, secretmanager, artifactregistry, storage, logging, monitoring, iam, iamcredentials, sts, cloudresourcemanager |
| Network | Private Services Access range + VPC peering (Cloud SQL private IP), global static IP for the HTTPS load balancer |
| Database | Cloud SQL PostgreSQL 16 instance (private IP only), `cropguard` database |
| Compute | GKE Autopilot cluster `cropguard-cluster` |
| Storage | uploads bucket (private), artifacts bucket (trained model for CI builds) |
| Registry | Artifact Registry `cropguard` |
| Secrets | 5 Secret Manager secrets (containers only) |
| Identity | app service account + roles + Workload Identity binding; CI deployer service account + Workload Identity Federation pool/provider for GitHub |
| Observability | log-based metric (HTTP 5xx), email notification channel, alert policy, dashboard |

Existing resources were adopted with `import` blocks (`imports.tf`).

## Not managed by Terraform (and why)

| Resource | Reason |
|---|---|
| Secret **values** and the Cloud SQL user password | Would be stored in plain text in Terraform state. Added once with `gcloud secrets versions add`. |
| Terraform state bucket `cropguard-ai-509423-tfstate` | Bootstrap: it must exist before Terraform can store state. |
| Kubernetes objects (Deployment, Service, Ingress, HPA, PDB, ManagedCertificate, BackendConfig, FrontendConfig, ServiceAccount) | Declared in `k8s/`, applied with kubectl; the image tag is updated by the CI pipeline on every push. |
| HTTPS load balancer, NEGs, Google-managed certificate | Created and owned by the GKE Ingress controller from `k8s/ingress.yaml`. |
| Billing budget ($50/month, 20/50/100% alerts) | Lives on the billing account, not in the project; kept as set up in Milestone 2. |
| Legacy VM `app-vm`, its static IP `app-vm-ip`, firewall rules, `cropguard-vm-sa` | Milestones 2-4 deployment, retired (stopped) after the move to GKE; kept for reference/rollback, not part of the running system. |
| Default VPC network | Created automatically by Google with the project. |
