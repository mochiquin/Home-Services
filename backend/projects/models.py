from django.db import models


class Project(models.Model):
    """A software project tracked in the system.

    Represents a single repository URL and its default branch. The owner_profile
    is protected from deletion to keep ownership history intact.
    """

    name = models.CharField(max_length=200, db_index=True)
    repo_url = models.URLField(max_length=255, unique=True)
    default_branch = models.CharField(max_length=100, blank=True, null=True)
    owner_profile = models.ForeignKey(
        "accounts.UserProfile", on_delete=models.PROTECT, related_name="owned_projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Project({self.name})"

class ProjectMember(models.Model):
    """Membership of a profile in a project with a specific role."""
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MAINTAINER = "maintainer", "Maintainer"
        REVIEWER = "reviewer", "Reviewer"
        MEMBER = "member", "Member"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=40, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "profile"], name="uq_project_member"),
        ]
        indexes = [models.Index(fields=["project", "role"], name="idx_member_project_role")]

    def __str__(self) -> str:
        return f"ProjectMember(project_id={self.project_id}, profile_id={self.profile_id}, role={self.role})"
