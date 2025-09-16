from django.db import models
from projects.models import Project


class Contributor(models.Model):
    """A person/account contributing code to one or more projects."""

    github_login = models.CharField(max_length=191, unique=True)
    email = models.EmailField(blank=True, null=True)
    affiliation = models.CharField(max_length=191, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["github_login"], name="idx_contrib_login")]

    def __str__(self) -> str:
        return self.github_login

class ProjectContributor(models.Model):
    """Per-project statistics for a contributor."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="contributors")
    contributor = models.ForeignKey("Contributor", on_delete=models.PROTECT, related_name="projects")
    commits_count = models.IntegerField(default=0)
    last_active_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "contributor"], name="uq_proj_contrib"),
        ]
        indexes = [models.Index(fields=["project", "commits_count"], name="idx_proj_contrib_stats")]

    def __str__(self) -> str:
        return f"ProjectContributor(project_id={self.project_id}, contributor_id={self.contributor_id})"

class CodeFile(models.Model):
    """A single source file within a project, with optional metadata."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="code_files")
    # Keep unique index within MySQL index limits (utf8mb4 -> 255 chars safe under 3072 bytes)
    path = models.CharField(max_length=255)
    language = models.CharField(max_length=40, blank=True, null=True)
    loc = models.IntegerField(blank=True, null=True)
    last_modified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "path"], name="uq_codefile_project_path"),
        ]
        indexes = [models.Index(fields=["project", "language"], name="idx_codefile_proj_lang")]

    def __str__(self) -> str:
        return f"{self.path} (project_id={self.project_id})"

class Commit(models.Model):
    """A commit in a project's VCS history."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="commits")
    sha = models.CharField(max_length=64)
    author_contributor = models.ForeignKey(
        Contributor, on_delete=models.SET_NULL, null=True, blank=True, related_name="authored_commits"
    )
    authored_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "sha"], name="uq_commit_sha"),
        ]
        indexes = [models.Index(fields=["project", "authored_at"], name="idx_commit_project_time")]

    def __str__(self) -> str:
        return f"Commit({self.sha[:12]})"
