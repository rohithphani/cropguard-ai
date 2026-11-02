# ─── Log-based metric: counts HTTP 5xx responses ───────────────────────────────
# Every request writes one JSON log line, e.g.
#   {"severity":"ERROR","message":"request","path":"/simulate-error","method":"GET","status":500,...}
# GKE ships stdout to Cloud Logging, which parses it into jsonPayload.
resource "google_logging_metric" "http_5xx" {
  name        = "cropguard_http_5xx_count"
  description = "HTTP 5xx responses returned by the CropGuard app (one per JSON request log line with status >= 500)"
  filter      = "resource.type=\"k8s_container\" AND resource.labels.cluster_name=\"cropguard-cluster\" AND resource.labels.container_name=\"web\" AND jsonPayload.message=\"request\" AND jsonPayload.status>=500"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "CropGuard HTTP 5xx count"
    labels {
      key         = "path"
      value_type  = "STRING"
      description = "Request path"
    }
    labels {
      key         = "status"
      value_type  = "STRING"
      description = "HTTP status code"
    }
  }
  label_extractors = {
    "path"   = "EXTRACT(jsonPayload.path)"
    "status" = "EXTRACT(jsonPayload.status)"
  }
}

# ─── Where alerts go ───────────────────────────────────────────────────────────
resource "google_monitoring_notification_channel" "email" {
  display_name = "CropGuard team email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

# ─── Alert: any 5xx in a 1-minute window ───────────────────────────────────────
resource "google_monitoring_alert_policy" "http_5xx" {
  display_name = "CropGuard - HTTP 5xx errors"
  combiner     = "OR"
  severity     = "ERROR"

  conditions {
    display_name = "HTTP 5xx responses > 0 (1 min)"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.http_5xx.name}\" AND resource.type=\"k8s_container\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    mime_type = "text/markdown"
    content   = "CropGuard returned HTTP 5xx errors. Check the JSON request logs: Logs Explorer, `jsonPayload.message=\"request\" AND jsonPayload.status>=500`, and the CropGuard dashboard."
  }
}

# ─── Dashboard: errors + resource usage ────────────────────────────────────────
locals {
  web = "resource.type=\"k8s_container\" resource.label.\"cluster_name\"=\"cropguard-cluster\" resource.label.\"container_name\"=\"web\""

  xy = {
    for k, v in {
      errors = {
        title   = "HTTP 5xx errors (log-based metric, per minute)"
        filter  = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.http_5xx.name}\" resource.type=\"k8s_container\""
        aligner = "ALIGN_SUM", reducer = "REDUCE_SUM", group = [], plot = "STACKED_BAR"
      }
      requests = {
        title   = "Load balancer requests/s by response class"
        filter  = "metric.type=\"loadbalancing.googleapis.com/https/request_count\" resource.type=\"https_lb_rule\""
        aligner = "ALIGN_RATE", reducer = "REDUCE_SUM", group = ["metric.label.\"response_code_class\""], plot = "LINE"
      }
      cpu = {
        title   = "CPU usage per pod (cores)"
        filter  = "metric.type=\"kubernetes.io/container/cpu/core_usage_time\" ${local.web}"
        aligner = "ALIGN_RATE", reducer = "REDUCE_SUM", group = ["resource.label.\"pod_name\""], plot = "LINE"
      }
      memory = {
        title   = "Memory used per pod (bytes)"
        filter  = "metric.type=\"kubernetes.io/container/memory/used_bytes\" ${local.web} metric.label.\"memory_type\"=\"non-evictable\""
        aligner = "ALIGN_MEAN", reducer = "REDUCE_SUM", group = ["resource.label.\"pod_name\""], plot = "LINE"
      }
      pods = {
        title   = "Running app pods"
        filter  = "metric.type=\"kubernetes.io/container/uptime\" ${local.web}"
        aligner = "ALIGN_MEAN", reducer = "REDUCE_COUNT", group = [], plot = "LINE"
      }
    } : k => {
      title = v.title
      xyChart = {
        chartOptions = { mode = "COLOR" }
        dataSets = [{
          minAlignmentPeriod = "60s"
          plotType           = v.plot
          targetAxis         = "Y1"
          timeSeriesQuery = {
            timeSeriesFilter = {
              filter = v.filter
              aggregation = merge(
                { alignmentPeriod = "60s", perSeriesAligner = v.aligner, crossSeriesReducer = v.reducer },
                { for name, fields in { groupByFields = v.group } : name => fields if length(fields) > 0 }
              )
            }
          }
        }]
        timeshiftDuration = "0s"
        yAxis             = { scale = "LINEAR" }
      }
    }
  }
}

resource "google_monitoring_dashboard" "cropguard" {
  dashboard_json = jsonencode({
    displayName = "CropGuard - errors and resources"
    mosaicLayout = {
      columns = 48
      tiles = [
        { width = 24, height = 16, widget = local.xy.errors },
        { xPos = 24, width = 24, height = 16, widget = { title = "5xx alert policy", alertChart = { name = google_monitoring_alert_policy.http_5xx.name } } },
        { yPos = 16, width = 24, height = 16, widget = local.xy.cpu },
        { xPos = 24, yPos = 16, width = 24, height = 16, widget = local.xy.memory },
        { yPos = 32, width = 24, height = 16, widget = local.xy.requests },
        { xPos = 24, yPos = 32, width = 24, height = 16, widget = local.xy.pods },
      ]
    }
  })
}
