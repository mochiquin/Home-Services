import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Contributor, ProjectContributor, CodeFile, Commit
from projects.models import Project
from rest_framework import serializers
from common.response import ApiResponse
from common.pagination import DefaultPagination

# Initialize logger for contributors API
logger = logging.getLogger(__name__)

# Serializers
class ContributorSerializer(serializers.ModelSerializer):
    """Serializer for Contributor model"""
    projects_count = serializers.SerializerMethodField()
    total_commits = serializers.SerializerMethodField()
    
    class Meta:
        model = Contributor
        fields = ['id', 'github_login', 'email', 'affiliation', 'created_at', 'updated_at', 
                 'projects_count', 'total_commits']
        read_only_fields = ['id', 'created_at', 'updated_at', 'projects_count', 'total_commits']
    
    def get_projects_count(self, obj):
        return obj.projects.count()
    
    def get_total_commits(self, obj):
        return obj.projects.aggregate(total=Sum('commits_count'))['total'] or 0

class ProjectContributorSerializer(serializers.ModelSerializer):
    """Serializer for ProjectContributor model"""
    contributor_login = serializers.CharField(source='contributor.github_login', read_only=True)
    contributor_email = serializers.CharField(source='contributor.email', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = ProjectContributor
        fields = ['id', 'project', 'contributor', 'contributor_login', 'contributor_email',
                 'project_name', 'commits_count', 'last_active_at']
        read_only_fields = ['id', 'contributor_login', 'contributor_email', 'project_name']

class CodeFileSerializer(serializers.ModelSerializer):
    """Serializer for CodeFile model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = CodeFile
        fields = ['id', 'project', 'project_name', 'path', 'language', 'loc', 'last_modified_at']
        read_only_fields = ['id', 'project_name']

class CommitSerializer(serializers.ModelSerializer):
    """Serializer for Commit model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    author_login = serializers.CharField(source='author_contributor.github_login', read_only=True)
    
    class Meta:
        model = Commit
        fields = ['id', 'project', 'project_name', 'sha', 'author_contributor', 
                 'author_login', 'authored_at']
        read_only_fields = ['id', 'project_name', 'author_login']

# ViewSets
class ContributorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contributors.
    Provides CRUD operations for contributor accounts with project statistics.
    """
    queryset = Contributor.objects.all()
    serializer_class = ContributorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """
        Filter queryset based on query parameters.
        Supports search by github_login, email, and affiliation.
        """
        queryset = Contributor.objects.select_related().prefetch_related('projects')
        
        # Search functionality
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(github_login__icontains=search) |
                Q(email__icontains=search) |
                Q(affiliation__icontains=search)
            )
        
        # Filter by affiliation
        affiliation = self.request.query_params.get('affiliation', '')
        if affiliation:
            queryset = queryset.filter(affiliation__icontains=affiliation)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """List contributors with logging"""
        user_id = request.user.id if request.user else None
        logger.info("Contributors list request", extra={
            'user_id': user_id,
            'search': request.query_params.get('search', ''),
            'affiliation': request.query_params.get('affiliation', '')
        })
        
        try:
            response = super().list(request, *args, **kwargs)
            logger.debug("Contributors list retrieved successfully", extra={
                'user_id': user_id,
                'count': response.data.get('count', 0) if hasattr(response, 'data') else 0
            })
            return response
        except Exception as e:
            logger.error("Failed to retrieve contributors list", extra={
                'user_id': user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retrieve contributors",
                error_code="CONTRIBUTORS_LIST_ERROR"
            )
    
    def create(self, request, *args, **kwargs):
        """Create new contributor with logging"""
        user_id = request.user.id if request.user else None
        github_login = request.data.get('github_login', '')
        
        logger.info("Creating new contributor", extra={
            'user_id': user_id,
            'github_login': github_login
        })
        
        try:
            response = super().create(request, *args, **kwargs)
            logger.info("Contributor created successfully", extra={
                'user_id': user_id,
                'github_login': github_login,
                'contributor_id': response.data.get('id') if hasattr(response, 'data') else None
            })
            return response
        except Exception as e:
            logger.error("Failed to create contributor", extra={
                'user_id': user_id,
                'github_login': github_login,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to create contributor",
                error_code="CONTRIBUTOR_CREATE_ERROR"
            )
    
    @action(detail=True, methods=['get'])
    def projects(self, request, pk=None):
        """Get all projects for a specific contributor"""
        user_id = request.user.id if request.user else None
        contributor = self.get_object()
        
        logger.info("Contributor projects request", extra={
            'user_id': user_id,
            'contributor_id': contributor.id,
            'github_login': contributor.github_login
        })
        
        try:
            project_contributors = contributor.projects.select_related('project').all()
            data = ProjectContributorSerializer(project_contributors, many=True).data
            
            logger.debug("Contributor projects retrieved successfully", extra={
                'user_id': user_id,
                'contributor_id': contributor.id,
                'projects_count': len(data)
            })
            
            return ApiResponse.success(
                data=data,
                message=f"Projects for contributor {contributor.github_login} retrieved successfully"
            )
        except Exception as e:
            logger.error("Failed to retrieve contributor projects", extra={
                'user_id': user_id,
                'contributor_id': contributor.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retrieve contributor projects",
                error_code="CONTRIBUTOR_PROJECTS_ERROR"
            )
    
    @action(detail=True, methods=['get'])
    def commits(self, request, pk=None):
        """Get all commits for a specific contributor"""
        user_id = request.user.id if request.user else None
        contributor = self.get_object()
        
        logger.info("Contributor commits request", extra={
            'user_id': user_id,
            'contributor_id': contributor.id,
            'github_login': contributor.github_login
        })
        
        try:
            commits = contributor.authored_commits.select_related('project').all()
            
            # Apply pagination
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(commits, request)
            if page is not None:
                serializer = CommitSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = CommitSerializer(commits, many=True)
            
            logger.debug("Contributor commits retrieved successfully", extra={
                'user_id': user_id,
                'contributor_id': contributor.id,
                'commits_count': len(serializer.data)
            })
            
            return ApiResponse.success(
                data=serializer.data,
                message=f"Commits for contributor {contributor.github_login} retrieved successfully"
            )
        except Exception as e:
            logger.error("Failed to retrieve contributor commits", extra={
                'user_id': user_id,
                'contributor_id': contributor.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retrieve contributor commits",
                error_code="CONTRIBUTOR_COMMITS_ERROR"
            )

class ProjectContributorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing project-contributor relationships.
    Handles per-project statistics for contributors.
    """
    queryset = ProjectContributor.objects.select_related('project', 'contributor').all()
    serializer_class = ProjectContributorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on project and contributor parameters"""
        queryset = ProjectContributor.objects.select_related('project', 'contributor')
        
        # Filter by project
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by contributor
        contributor_id = self.request.query_params.get('contributor_id', '')
        if contributor_id:
            queryset = queryset.filter(contributor_id=contributor_id)
        
        return queryset.order_by('-commits_count', '-last_active_at')

class CodeFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing code files within projects.
    Provides file metadata and statistics.
    """
    queryset = CodeFile.objects.select_related('project').all()
    serializer_class = CodeFileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on project and language parameters"""
        queryset = CodeFile.objects.select_related('project')
        
        # Filter by project
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by language
        language = self.request.query_params.get('language', '')
        if language:
            queryset = queryset.filter(language__icontains=language)
        
        # Search by file path
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(path__icontains=search)
        
        return queryset.order_by('project_id', 'path')

class CommitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing commits within projects.
    Provides commit history and author information.
    """
    queryset = Commit.objects.select_related('project', 'author_contributor').all()
    serializer_class = CommitSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on project and contributor parameters"""
        queryset = Commit.objects.select_related('project', 'author_contributor')
        
        # Filter by project
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by contributor
        contributor_id = self.request.query_params.get('contributor_id', '')
        if contributor_id:
            queryset = queryset.filter(author_contributor_id=contributor_id)
        
        return queryset.order_by('-authored_at')

# Statistics endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contributor_stats(request):
    """
    Get comprehensive contributor statistics.
    Returns aggregated data about contributors, projects, and activity.
    """
    user_id = request.user.id if request.user else None
    logger.info("Contributor statistics request", extra={
        'user_id': user_id
    })
    
    try:
        # Aggregate statistics
        total_contributors = Contributor.objects.count()
        active_contributors = Contributor.objects.filter(
            projects__last_active_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).distinct().count()
        
        # Top contributors by commits
        top_contributors = ProjectContributor.objects.values(
            'contributor__github_login', 'contributor__id'
        ).annotate(
            total_commits=Sum('commits_count')
        ).order_by('-total_commits')[:10]
        
        # Language statistics
        language_stats = CodeFile.objects.values('language').annotate(
            file_count=Count('id'),
            total_loc=Sum('loc')
        ).order_by('-file_count')[:10]
        
        stats = {
            'total_contributors': total_contributors,
            'active_contributors': active_contributors,
            'total_projects': Project.objects.count(),
            'total_code_files': CodeFile.objects.count(),
            'total_commits': Commit.objects.count(),
            'top_contributors': list(top_contributors),
            'language_statistics': list(language_stats),
            'generated_at': timezone.now().isoformat()
        }
        
        logger.info("Contributor statistics retrieved successfully", extra={
            'user_id': user_id,
            'total_contributors': total_contributors,
            'active_contributors': active_contributors
        })
        
        return ApiResponse.success(
            data=stats,
            message="Contributor statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve contributor statistics", extra={
            'user_id': user_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to retrieve contributor statistics",
            error_code="CONTRIBUTOR_STATS_ERROR"
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_contributor_analysis(request, project_id):
    """
    Get detailed contributor analysis for a specific project.
    Returns contributor activity, commit patterns, and code ownership.
    """
    user_id = request.user.id if request.user else None
    logger.info("Project contributor analysis request", extra={
        'user_id': user_id,
        'project_id': project_id
    })
    
    try:
        # Verify project exists
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            logger.warning("Project not found for contributor analysis", extra={
                'user_id': user_id,
                'project_id': project_id
            })
            return ApiResponse.not_found(
                error_message="Project not found",
                error_code="PROJECT_NOT_FOUND"
            )
        
        # Get project contributors with statistics
        contributors = ProjectContributor.objects.filter(
            project_id=project_id
        ).select_related('contributor').order_by('-commits_count')
        
        # Get file distribution by contributor
        file_stats = CodeFile.objects.filter(project_id=project_id).values(
            'language'
        ).annotate(
            file_count=Count('id'),
            total_loc=Sum('loc')
        )
        
        # Get commit timeline
        recent_commits = Commit.objects.filter(
            project_id=project_id,
            authored_at__gte=timezone.now() - timezone.timedelta(days=90)
        ).select_related('author_contributor').order_by('-authored_at')[:50]
        
        analysis = {
            'project': {
                'id': project.id,
                'name': project.name,
                'description': getattr(project, 'description', '')
            },
            'contributors': ProjectContributorSerializer(contributors, many=True).data,
            'file_statistics': list(file_stats),
            'recent_commits': CommitSerializer(recent_commits, many=True).data,
            'summary': {
                'total_contributors': contributors.count(),
                'total_commits': contributors.aggregate(total=Sum('commits_count'))['total'] or 0,
                'total_files': CodeFile.objects.filter(project_id=project_id).count(),
                'analysis_date': timezone.now().isoformat()
            }
        }
        
        logger.info("Project contributor analysis completed successfully", extra={
            'user_id': user_id,
            'project_id': project_id,
            'contributors_count': contributors.count()
        })
        
        return ApiResponse.success(
            data=analysis,
            message=f"Contributor analysis for project {project.name} retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve project contributor analysis", extra={
            'user_id': user_id,
            'project_id': project_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to retrieve contributor analysis",
            error_code="PROJECT_ANALYSIS_ERROR"
        )
