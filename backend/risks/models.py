from django.db import models
from projects.models import Project
from coordination.models import CoordinationRun

class RiskAssessment(models.Model):
    """A single risk assessment record produced from a coordination run."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="risks")
    run = models.ForeignKey(CoordinationRun, on_delete=models.CASCADE, related_name="risks")
    risk_type = models.CharField(max_length=60)  # e.g., bus_factor_low / coord_gap / ...
    risk_score = models.DecimalField(max_digits=6, decimal_places=3)
    recommendation = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "run", "risk_type"], name="uq_risk"),
        ]
        indexes = [models.Index(fields=["project", "risk_score"], name="idx_risk_proj_score")]

    def __str__(self) -> str:
        return f"Risk({self.risk_type}, project_id={self.project_id})"

class AlertRule(models.Model):
    """A rule that evaluates metrics and raises alert events when matched."""
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARN = "warn", "Warn"
        CRITICAL = "critical", "Critical"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="alert_rules")
    name = models.CharField(max_length=160)
    condition = models.JSONField(default=dict)  # e.g., {"metric":"MC-STC","op":"<","value":0.25,"for":"7d"}
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.WARN)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey("accounts.UserProfile", on_delete=models.PROTECT, related_name="created_alert_rules")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["project"], name="idx_rule_project")]

    def __str__(self) -> str:
        return f"AlertRule({self.name})"

class AlertEvent(models.Model):
    """A concrete alert event instance produced by an alert rule."""
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACK = "ack", "Acknowledged"
        CLOSED = "closed", "Closed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="alert_events")
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="events")
    triggered_at = models.DateTimeField(auto_now_add=True)
    current_value = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    run = models.ForeignKey(CoordinationRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="alert_events")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)

    class Meta:
        indexes = [
            models.Index(fields=["project", "triggered_at"], name="idx_event_project_time"),
            models.Index(fields=["status"], name="idx_event_status"),
        ]

    def __str__(self) -> str:
        return f"AlertEvent(project_id={self.project_id}, rule_id={self.rule_id}, status={self.status})"
