from django.db import models
from projects.models import Project
from .enums import FunctionalRole, ActivityLevel, RoleConfidenceLevel


class Contributor(models.Model):
    """A person/account contributing code to one or more projects."""

    github_login = models.CharField(max_length=191, unique=True)
    email = models.EmailField(blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True, help_text="Full name of contributor (user can add)")
    affiliation = models.CharField(max_length=191, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def display_name(self):
        """Return full name if available, otherwise github_login."""
        return self.full_name if self.full_name else self.github_login

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
    
    # TNM Analysis Data
    tnm_user_id = models.CharField(max_length=50, blank=True, null=True, help_text="User ID from TNM analysis")
    files_modified = models.IntegerField(default=0, help_text="Number of files modified")
    total_modifications = models.IntegerField(default=0, help_text="Total modifications across all files")
    avg_modifications_per_file = models.FloatField(default=0.0, help_text="Average modifications per file")
    
    # MC-STC Classification
    functional_role = models.CharField(
        max_length=20, 
        choices=FunctionalRole.choices, 
        default=FunctionalRole.UNCLASSIFIED,
        help_text="Functional role for MC-STC calculation"
    )
    is_core_contributor = models.BooleanField(default=False, help_text="Is this a core contributor")
    role_confidence = models.FloatField(default=0.0, help_text="Confidence score for role classification (0-1)")
    
    # TNM analysis metadata
    last_tnm_analysis = models.DateTimeField(blank=True, null=True, help_text="Last TNM analysis timestamp")
    tnm_branch = models.CharField(max_length=100, blank=True, help_text="Branch analyzed by TNM")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "contributor"], name="uq_proj_contrib"),
        ]
        indexes = [
            models.Index(fields=["project", "commits_count"], name="idx_proj_contrib_stats"),
            models.Index(fields=["project", "functional_role"], name="idx_proj_contrib_role"),
            models.Index(fields=["project", "total_modifications"], name="idx_proj_contrib_mods"),
            models.Index(fields=["project", "is_core_contributor"], name="idx_proj_contrib_core"),
        ]

    def __str__(self) -> str:
        return f"ProjectContributor(project_id={self.project_id}, contributor_id={self.contributor_id})"
    
    @property
    def activity_level(self):
        """Calculate activity level based on modifications."""
        return ActivityLevel.get_level(self.total_modifications).value
    
    @property 
    def activity_level_enum(self):
        """Get activity level as enum for programmatic use."""
        return ActivityLevel.get_level(self.total_modifications)
    
    def get_role_confidence_level(self):
        """Get confidence level for role classification."""
        return RoleConfidenceLevel.get_confidence_for_stats(
            self.total_modifications, 
            self.files_modified, 
            self.avg_modifications_per_file
        )

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
