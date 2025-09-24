from rest_framework import serializers
from .models import Contributor, ProjectContributor, CodeFile, Commit


class ContributorSerializer(serializers.ModelSerializer):
    """Serializer for Contributor model."""
    
    class Meta:
        model = Contributor
        fields = ['id', 'github_login', 'email', 'affiliation', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectContributorSerializer(serializers.ModelSerializer):
    """Serializer for ProjectContributor model with role classification."""
    
    contributor = ContributorSerializer(read_only=True)
    activity_level = serializers.ReadOnlyField()
    functional_role_display = serializers.CharField(source='get_functional_role_display', read_only=True)
    
    class Meta:
        model = ProjectContributor
        fields = [
            'id', 'contributor', 'commits_count', 'last_active_at',
            'tnm_user_id', 'files_modified', 'total_modifications', 
            'avg_modifications_per_file', 'functional_role', 'functional_role_display',
            'is_core_contributor', 'role_confidence', 'activity_level',
            'last_tnm_analysis', 'tnm_branch'
        ]
        read_only_fields = [
            'id', 'contributor', 'tnm_user_id', 'files_modified', 
            'total_modifications', 'avg_modifications_per_file', 
            'role_confidence', 'last_tnm_analysis', 'tnm_branch'
        ]


class ProjectContributorClassificationSerializer(serializers.ModelSerializer):
    """Serializer for updating contributor role classifications."""
    
    contributor_name = serializers.CharField(source='contributor.github_login', read_only=True)
    contributor_email = serializers.CharField(source='contributor.email', read_only=True)
    activity_level = serializers.ReadOnlyField()
    functional_role_display = serializers.CharField(source='get_functional_role_display', read_only=True)
    
    class Meta:
        model = ProjectContributor
        fields = [
            'id', 'contributor_name', 'contributor_email', 'total_modifications',
            'files_modified', 'functional_role', 'functional_role_display', 
            'is_core_contributor', 'role_confidence', 'activity_level'
        ]
        read_only_fields = [
            'id', 'contributor_name', 'contributor_email', 'total_modifications',
            'files_modified', 'role_confidence', 'activity_level'
        ]


class TNMAnalysisResultSerializer(serializers.Serializer):
    """Serializer for TNM analysis results."""
    
    total_contributors = serializers.IntegerField()
    contributors_created = serializers.IntegerField()
    contributors_updated = serializers.IntegerField()
    analysis_time = serializers.DateTimeField()
    branch = serializers.CharField()
    project_id = serializers.UUIDField(source='project.id', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)


class FunctionalRoleChoiceSerializer(serializers.Serializer):
    """Serializer for functional role choices."""
    
    value = serializers.CharField()
    label = serializers.CharField()


class CodeFileSerializer(serializers.ModelSerializer):
    """Serializer for CodeFile model."""
    
    class Meta:
        model = CodeFile
        fields = ['id', 'path', 'language', 'loc', 'last_modified_at']
        read_only_fields = ['id']


class CommitSerializer(serializers.ModelSerializer):
    """Serializer for Commit model."""
    
    author_name = serializers.CharField(source='author_contributor.github_login', read_only=True)
    
    class Meta:
        model = Commit
        fields = ['id', 'sha', 'author_name', 'authored_at']
        read_only_fields = ['id']
