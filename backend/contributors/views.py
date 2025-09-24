import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Contributor, ProjectContributor, CodeFile, Commit
from projects.models import Project
from .enums import FunctionalRole
from .services import TNMDataAnalysisService
from rest_framework import serializers
from common.response import ApiResponse
from common.pagination import DefaultPagination
import os
from django.conf import settings

# Initialize logger for contributors API
logger = logging.getLogger(__name__)

# Serializers
class ContributorSerializer(serializers.ModelSerializer):
    """Serializer for Contributor model"""
    projects_count = serializers.SerializerMethodField()
    total_commits = serializers.SerializerMethodField()
    display_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Contributor
        fields = ['id', 'github_login', 'email', 'full_name', 'display_name',
                 'affiliation', 'created_at', 'updated_at', 'projects_count', 'total_commits']
        read_only_fields = ['id', 'created_at', 'updated_at', 'projects_count', 'total_commits', 'display_name']
    
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


# New TNM Classification Serializers
class ProjectContributorClassificationSerializer(serializers.ModelSerializer):
    """Serializer for updating contributor role classifications."""
    
    contributor_name = serializers.CharField(source='contributor.github_login', read_only=True)
    contributor_email = serializers.CharField(source='contributor.email', read_only=True)
    activity_level = serializers.SerializerMethodField()
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
            'files_modified', 'role_confidence'
        ]
    
    def get_activity_level(self, obj):
        return obj.activity_level


class FunctionalRoleChoiceSerializer(serializers.Serializer):
    """Serializer for functional role choices."""
    value = serializers.CharField()
    label = serializers.CharField()


# New API Endpoints for TNM Analysis and Role Classification

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_tnm_contributors(request, project_id):
    """
    Analyze TNM output data and populate contributor information.
    
    POST /api/contributors/projects/{project_id}/analyze_tnm/
    Body: {
        "tnm_output_dir": "/path/to/tnm/output", (optional, auto-detected)
        "branch": "main" (optional)
    }
    """
    try:
        # Get project and verify permissions
        project = Project.objects.get(id=project_id)
        user_profile = request.user.profile
        
        # Check permissions - only project members can analyze
        if not (project.owner_profile == user_profile or 
                project.members.filter(profile=user_profile).exists()):
            return ApiResponse.forbidden("Only project members can analyze contributors")
        
        # Get TNM output directory
        payload = request.data or {}
        tnm_output_dir = payload.get('tnm_output_dir')
        branch = payload.get('branch', 'unknown')
        
        # Auto-detect TNM output directory if not provided
        if not tnm_output_dir:
            repos_root = getattr(settings, 'TNM_OUTPUT_DIR', '/app/tnm_output')
            tnm_output_dir = f"{repos_root}/project_{project.id}_{branch.replace('/', '_')}"
        
        if not os.path.exists(tnm_output_dir):
            return ApiResponse.error(
                error_message=f"TNM output directory not found: {tnm_output_dir}",
                error_code="TNM_OUTPUT_NOT_FOUND"
            )
        
        # Analyze TNM data
        analysis_result = TNMDataAnalysisService.analyze_assignment_matrix(
            project, tnm_output_dir, branch
        )
        
        logger.info(f"TNM contributor analysis completed for project {project.id}", extra={
            'project_id': project_id,
            'user_id': request.user.id,
            'contributors_processed': analysis_result['total_contributors']
        })
        
        return ApiResponse.success(
            data=analysis_result,
            message=f"Analyzed {analysis_result['total_contributors']} contributors from TNM data"
        )
        
    except Project.DoesNotExist:
        return ApiResponse.not_found("Project not found")
    except Exception as e:
        logger.error(f"TNM contributor analysis failed: {e}", extra={
            'project_id': project_id,
            'user_id': request.user.id
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to analyze TNM contributor data",
            error_code="TNM_ANALYSIS_ERROR"
        )


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def project_contributors_classification(request, project_id):
    """
    Get or update contributor role classifications for MC-STC analysis.
    
    GET /api/contributors/projects/{project_id}/classification/
    Query params: page, page_size, role, activity_level, search
    
    PATCH /api/contributors/projects/{project_id}/classification/
    Body: [
        {
            "id": 1,
            "functional_role": "core_developer",
            "is_core_contributor": true
        },
        ...
    ]
    """
    try:
        # Get project and verify permissions
        project = Project.objects.get(id=project_id)
        user_profile = request.user.profile
        
        # Check permissions
        if not (project.owner_profile == user_profile or 
                project.members.filter(profile=user_profile).exists()):
            return ApiResponse.forbidden("Only project members can access contributor classifications")
        
        if request.method == 'GET':
            # Get contributors with pagination and filtering
            queryset = ProjectContributor.objects.filter(project=project).select_related('contributor')
            
            # Apply filters
            role = request.GET.get('role')
            if role:
                queryset = queryset.filter(functional_role=role)
            
            activity_level = request.GET.get('activity_level')
            if activity_level:
                if activity_level == 'high':
                    queryset = queryset.filter(total_modifications__gte=1000)
                elif activity_level == 'medium':
                    queryset = queryset.filter(total_modifications__gte=100, total_modifications__lt=1000)
                elif activity_level == 'low':
                    queryset = queryset.filter(total_modifications__gte=10, total_modifications__lt=100)
                elif activity_level == 'minimal':
                    queryset = queryset.filter(total_modifications__lt=10)
            
            search = request.GET.get('search')
            if search:
                queryset = queryset.filter(
                    Q(contributor__github_login__icontains=search) |
                    Q(contributor__email__icontains=search)
                )
            
            # Order by total modifications descending
            queryset = queryset.order_by('-total_modifications')
            
            # Apply pagination
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(queryset, request)
            
            serializer = ProjectContributorClassificationSerializer(page, many=True)
            
            return paginator.get_paginated_response(
                serializer.data,
                message=f"Retrieved {len(serializer.data)} contributors for classification"
            )
        
        elif request.method == 'PATCH':
            # Batch update contributor classifications
            updates = request.data if isinstance(request.data, list) else [request.data]
            updated_count = 0
            
            for update in updates:
                contributor_id = update.get('id')
                if not contributor_id:
                    continue
                
                try:
                    contributor = ProjectContributor.objects.get(
                        id=contributor_id, 
                        project=project
                    )
                    
                    # Update fields
                    if 'functional_role' in update:
                        contributor.functional_role = update['functional_role']
                    if 'is_core_contributor' in update:
                        contributor.is_core_contributor = update['is_core_contributor']
                    
                    contributor.save(update_fields=['functional_role', 'is_core_contributor'])
                    updated_count += 1
                    
                except ProjectContributor.DoesNotExist:
                    logger.warning(f"Contributor {contributor_id} not found for project {project_id}")
                    continue
            
            logger.info(f"Updated {updated_count} contributor classifications", extra={
                'project_id': project_id,
                'user_id': request.user.id,
                'updated_count': updated_count
            })
            
            return ApiResponse.success(
                data={'updated_count': updated_count},
                message=f"Updated {updated_count} contributor classifications"
            )
        
    except Project.DoesNotExist:
        return ApiResponse.not_found("Project not found")
    except Exception as e:
        logger.error(f"Contributor classification operation failed: {e}", extra={
            'project_id': project_id,
            'user_id': request.user.id,
            'method': request.method
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to process contributor classifications",
            error_code="CLASSIFICATION_ERROR"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def functional_role_choices(request):
    """
    Get available functional role choices for contributor classification.
    
    GET /api/contributors/functional-role-choices/
    """
    try:
        choices = FunctionalRole.get_choices_dict()
        
        return ApiResponse.success(
            data={'choices': choices},
            message="Retrieved functional role choices"
        )
        
    except Exception as e:
        logger.error(f"Failed to get functional role choices: {e}", exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to retrieve role choices",
            error_code="ROLE_CHOICES_ERROR"
        )
