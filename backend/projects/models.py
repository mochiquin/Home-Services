"""
Projects API Models

This module provides models for Project and ProjectMember.
"""

import uuid
from django.db import models
from django.core.exceptions import ValidationError


class Project(models.Model):
    """
    Project model representing a software project with repository information.
    
    Fields:
    - id: UUID primary key
    - name: Project name (max 200 chars, indexed)
    - repo_url: Repository URL (unique)
    - default_branch: Default branch name
    - owner_profile: Foreign key to UserProfile (project owner)
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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


class ProjectRole:
    """Project role definitions with IDs and names."""
    
    # Role definitions with ID, value, and display name
    ROLES = {
        1: {"value": "owner", "name": "Owner", "description": "Full control over the project"},
        2: {"value": "maintainer", "name": "Maintainer", "description": "Can manage project settings and members"},
        3: {"value": "reviewer", "name": "Reviewer", "description": "Can review code and manage issues"}
    }
    
    @classmethod
    def get_role_by_id(cls, role_id):
        """Get role information by ID."""
        return cls.ROLES.get(role_id)
    
    @classmethod
    def get_role_by_value(cls, value):
        """Get role information by value."""
        for role_id, role_info in cls.ROLES.items():
            if role_info["value"] == value:
                return {"id": role_id, **role_info}
        return None
    
    @classmethod
    def get_all_roles(cls):
        """Get all available roles."""
        return {role_id: {"id": role_id, **role_info} for role_id, role_info in cls.ROLES.items()}
    
    @classmethod
    def is_valid_role_id(cls, role_id):
        """Check if role ID is valid."""
        return role_id in cls.ROLES
    
    @classmethod
    def is_valid_role_value(cls, value):
        """Check if role value is valid."""
        return any(role_info["value"] == value for role_info in cls.ROLES.values())


class ProjectMember(models.Model):
    """Membership of a profile in a project with a specific role."""
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MAINTAINER = "maintainer", "Maintainer"
        REVIEWER = "reviewer", "Reviewer"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REVIEWER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['project', 'profile']
        indexes = [
            models.Index(fields=['project', 'role']),
        ]

    def __str__(self) -> str:
        return f"ProjectMember({self.project.name}:{self.profile.user.username})"

    def clean(self):
        """Validate that a user cannot have multiple roles in the same project."""
        if self.pk:  # Only check for existing instances
            existing = ProjectMember.objects.filter(
                project=self.project, profile=self.profile
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError("User already has a role in this project.")