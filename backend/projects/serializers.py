"""
Projects API Serializers

This module provides serializers for Project and ProjectMember models.

Models:
- Project: name, repo_url, default_branch, owner_profile, created_at, updated_at
- ProjectMember: project, profile, role, joined_at

Validation Rules:
- Project names are required and limited to 200 characters
- Repository URLs must be valid HTTP/HTTPS or Git SSH URLs
- Each user can only have one role per project
- Project owners cannot be removed or have their role changed
- Repository URLs must be unique across all projects

Role Hierarchy:
1. owner: Full control over the project
2. maintainer: Can manage project settings and members
3. reviewer: Can review code and manage issues
4. member: Basic access to project resources
"""

from rest_framework import serializers
from .models import Project, ProjectMember
from accounts.models import UserProfile


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model with owner information."""
    
    owner_username = serializers.CharField(source='owner_profile.user.username', read_only=True)
    owner_email = serializers.EmailField(source='owner_profile.user.email', read_only=True)
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'repo_url', 'default_branch', 
            'owner_profile', 'owner_username', 'owner_email',
            'members_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_members_count(self, obj):
        """Get the number of members in the project."""
        return obj.members.count()
    
    def validate_repo_url(self, value):
        """Validate repository URL format."""
        if not value.startswith(('http://', 'https://', 'git@')):
            raise serializers.ValidationError("Repository URL must be a valid HTTP/HTTPS URL or Git SSH URL.")
        return value
    
    def create(self, validated_data):
        """Create a new project using service layer."""
        from .services import ProjectService
        
        # Use service layer to create project
        result = ProjectService.create_project(validated_data, validated_data['owner_profile'])
        return result['project']


class ProjectListSerializer(serializers.ModelSerializer):
    """Simplified serializer for project list views."""
    
    owner_username = serializers.CharField(source='owner_profile.user.username', read_only=True)
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'repo_url', 'default_branch',
            'owner_username', 'members_count', 'created_at'
        ]
    
    def get_members_count(self, obj):
        """Get the number of members in the project."""
        return obj.members.count()


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Serializer for ProjectMember model."""
    
    username = serializers.CharField(source='profile.user.username', read_only=True)
    email = serializers.EmailField(source='profile.user.email', read_only=True)
    first_name = serializers.CharField(source='profile.first_name', read_only=True)
    last_name = serializers.CharField(source='profile.last_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = ProjectMember
        fields = [
            'id', 'project', 'project_name', 'profile', 'username', 
            'email', 'first_name', 'last_name', 'role', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']
    
    def validate(self, data):
        """Validate that a user can only have one role per project."""
        project = data.get('project')
        profile = data.get('profile')
        
        if project and profile:
            existing_member = ProjectMember.objects.filter(
                project=project, 
                profile=profile
            ).exclude(id=self.instance.id if self.instance else None)
            
            if existing_member.exists():
                raise serializers.ValidationError(
                    "This user is already a member of this project."
                )
        
        return data


class ProjectMemberCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new project members."""
    
    username = serializers.CharField(write_only=True)
    
    class Meta:
        model = ProjectMember
        fields = ['project', 'username', 'role']
    
    def validate_username(self, value):
        """Validate that the username exists."""
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(username=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this username does not exist.")
    
    def create(self, validated_data):
        """Create a new project member using service layer."""
        from .services import ProjectService
        
        project = validated_data['project']
        username = validated_data.pop('username')
        role = validated_data['role']
        
        # Use service layer to add member (we need a user_profile for permission check)
        # This will be handled in the view where we have access to request.user
        from django.contrib.auth.models import User
        user = User.objects.get(username=username)
        profile = user.profile
        
        return ProjectMember.objects.create(
            project=project,
            profile=profile,
            role=role
        )


class ProjectStatsSerializer(serializers.Serializer):
    """Serializer for project statistics."""
    
    total_projects = serializers.IntegerField()
    total_members = serializers.IntegerField()
    projects_by_owner = serializers.DictField()
    recent_projects = ProjectListSerializer(many=True)
