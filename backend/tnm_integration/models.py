from django.db import models
from projects.models import Project


class TnmJob(models.Model):
    """A TNM job describing a mining/calculation run and its artifacts."""
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    # Temporary nullable to allow migrating legacy rows; backfill then set non-null in a follow-up migration.
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tnm_jobs", null=True, blank=True)
    repo_url = models.CharField(max_length=500)
    branch = models.CharField(max_length=100)
    command = models.CharField(max_length=120)  # miner or calculation name
    options = models.JSONField(default=dict, blank=True)
    args = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.QUEUED, db_index=True)
    error = models.TextField(blank=True, null=True)
    stdout_url = models.CharField(max_length=800, blank=True, null=True)
    stderr_url = models.CharField(max_length=800, blank=True, null=True)
    result_url = models.CharField(max_length=800, blank=True, null=True)
    created_by = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="created_tnm_jobs",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "status", "updated_at"], name="idx_job_project_status_time"),
            models.Index(fields=["command", "updated_at"], name="idx_job_command_time"),
        ]

    def __str__(self) -> str:
        return f"TnmJob(project_id={self.project_id}, cmd={self.command}, status={self.status})"

class JobArtifact(models.Model):
    """A file artifact produced by a job (e.g., JSON/HTML)."""
    job = models.ForeignKey(TnmJob, on_delete=models.CASCADE, related_name="artifacts")
    artifact_type = models.CharField(max_length=20)  # json/html/...
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=800)
    checksum = models.CharField(max_length=200, blank=True, null=True)
    size_bytes = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "name"], name="uq_jobartifact"),
        ]
        indexes = [models.Index(fields=["job", "artifact_type"], name="idx_artifact_job_type")]

    def __str__(self) -> str:
        return f"JobArtifact(job_id={self.job_id}, name={self.name})"

class JsonPayload(models.Model):
    """Structured JSON payload stored for a job under a logical name."""
    job = models.ForeignKey(TnmJob, on_delete=models.CASCADE, related_name="json_payloads")
    name = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    schema_version = models.CharField(max_length=50, blank=True, null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["job", "name"], name="uq_jsonpayload")]

    def __str__(self) -> str:
        return f"JsonPayload(job_id={self.job_id}, name={self.name})"

class MatrixChunk(models.Model):
    """Chunked storage for large matrices produced by TNM."""
    job = models.ForeignKey(TnmJob, on_delete=models.CASCADE, related_name="matrix_chunks")
    matrix_name = models.CharField(max_length=120)  # assignment_matrix / file_dependency_matrix / ...
    chunk_no = models.IntegerField()
    data = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "matrix_name", "chunk_no"], name="uq_matrix_chunk"),
        ]
        indexes = [models.Index(fields=["job", "matrix_name", "chunk_no"], name="idx_matrix_lookup")]

    def __str__(self) -> str:
        return f"MatrixChunk(job_id={self.job_id}, name={self.matrix_name}, chunk={self.chunk_no})"
