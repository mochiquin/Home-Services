import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import (
    CoordinationRun, TaEntry, TdEdge, CaEdge, CrEdge, 
    FunctionalClass, ContributorClassification
)
from projects.models import Project
# from tnm_integration.models import TnmJob  # Removed - TNM jobs no longer supported
from contributors.models import Contributor, CodeFile
from rest_framework import serializers
from common.response import ApiResponse
from common.pagination import DefaultPagination

# Initialize logger for coordination API
logger = logging.getLogger(__name__)

# Serializers
class CoordinationRunSerializer(serializers.ModelSerializer):
    """Serializer for CoordinationRun model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    job_status = serializers.CharField(source='job.status', read_only=True)
    
    class Meta:
        model = CoordinationRun
        fields = ['id', 'project', 'project_name', 'job', 'job_status', 'algorithm', 
                 'td_source', 'ca_source', 'class_config', 'time_window', 'score',
                 'cr_count', 'diff_count', 'created_at']
        read_only_fields = ['id', 'project_name', 'job_status', 'created_at']

class TaEntrySerializer(serializers.ModelSerializer):
    """Serializer for Task Assignment (TA) entries"""
    contributor_login = serializers.CharField(source='contributor.github_login', read_only=True)
    file_path = serializers.CharField(source='file.path', read_only=True)
    job_id = serializers.IntegerField(source='job.id', read_only=True)
    
    class Meta:
        model = TaEntry
        fields = ['id', 'job', 'job_id', 'contributor', 'contributor_login', 
                 'file', 'file_path', 'edit_count']
        read_only_fields = ['id', 'job_id', 'contributor_login', 'file_path']

class TdEdgeSerializer(serializers.ModelSerializer):
    """Serializer for Technical Dependency (TD) edges"""
    file_a_path = serializers.CharField(source='file_a.path', read_only=True)
    file_b_path = serializers.CharField(source='file_b.path', read_only=True)
    job_id = serializers.IntegerField(source='job.id', read_only=True)
    
    class Meta:
        model = TdEdge
        fields = ['id', 'job', 'job_id', 'file_a', 'file_a_path', 
                 'file_b', 'file_b_path', 'weight']
        read_only_fields = ['id', 'job_id', 'file_a_path', 'file_b_path']

class CaEdgeSerializer(serializers.ModelSerializer):
    """Serializer for Coordination Activity (CA) edges"""
    contributor_i_login = serializers.CharField(source='contributor_i.github_login', read_only=True)
    contributor_j_login = serializers.CharField(source='contributor_j.github_login', read_only=True)
    job_id = serializers.IntegerField(source='job.id', read_only=True)
    
    class Meta:
        model = CaEdge
        fields = ['id', 'job', 'job_id', 'contributor_i', 'contributor_i_login',
                 'contributor_j', 'contributor_j_login', 'weight', 'evidence']
        read_only_fields = ['id', 'job_id', 'contributor_i_login', 'contributor_j_login']

class CrEdgeSerializer(serializers.ModelSerializer):
    """Serializer for Coordination Requirement (CR) edges"""
    contributor_i_login = serializers.CharField(source='contributor_i.github_login', read_only=True)
    contributor_j_login = serializers.CharField(source='contributor_j.github_login', read_only=True)
    run_algorithm = serializers.CharField(source='run.algorithm', read_only=True)
    
    class Meta:
        model = CrEdge
        fields = ['id', 'run', 'run_algorithm', 'contributor_i', 'contributor_i_login',
                 'contributor_j', 'contributor_j_login', 'weight']
        read_only_fields = ['id', 'run_algorithm', 'contributor_i_login', 'contributor_j_login']

class FunctionalClassSerializer(serializers.ModelSerializer):
    """Serializer for FunctionalClass model"""
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FunctionalClass
        fields = ['id', 'code', 'name', 'description', 'members_count']
        read_only_fields = ['id', 'members_count']
    
    def get_members_count(self, obj):
        return obj.members.count()

class ContributorClassificationSerializer(serializers.ModelSerializer):
    """Serializer for ContributorClassification model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    contributor_login = serializers.CharField(source='contributor.github_login', read_only=True)
    class_name = serializers.CharField(source='class_ref.name', read_only=True)
    class_code = serializers.CharField(source='class_ref.code', read_only=True)
    
    class Meta:
        model = ContributorClassification
        fields = ['id', 'project', 'project_name', 'contributor', 'contributor_login',
                 'class_ref', 'class_name', 'class_code', 'basis_job', 'method',
                 'threshold', 'evidence']
        read_only_fields = ['id', 'project_name', 'contributor_login', 'class_name', 'class_code']

# ViewSets
class CoordinationRunViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing coordination runs.
    Provides CRUD operations for coordination analysis results.
    """
    queryset = CoordinationRun.objects.select_related('project', 'job').all()
    serializer_class = CoordinationRunSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = CoordinationRun.objects.select_related('project', 'job')
        
        # Filter by project
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by algorithm
        algorithm = self.request.query_params.get('algorithm', '')
        if algorithm:
            queryset = queryset.filter(algorithm=algorithm)
        
        # Filter by score range
        min_score = self.request.query_params.get('min_score', '')
        max_score = self.request.query_params.get('max_score', '')
        if min_score:
            queryset = queryset.filter(score__gte=min_score)
        if max_score:
            queryset = queryset.filter(score__lte=max_score)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """List coordination runs with logging"""
        user_id = request.user.id if request.user else None
        logger.info("Coordination runs list request", extra={
            'user_id': user_id,
            'project_id': request.query_params.get('project_id', ''),
            'algorithm': request.query_params.get('algorithm', '')
        })
        
        try:
            response = super().list(request, *args, **kwargs)
            logger.debug("Coordination runs list retrieved successfully", extra={
                'user_id': user_id,
                'count': response.data.get('count', 0) if hasattr(response, 'data') else 0
            })
            return response
        except Exception as e:
            logger.error("Failed to retrieve coordination runs list", extra={
                'user_id': user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retrieve coordination runs",
                error_code="COORDINATION_RUNS_LIST_ERROR"
            )
    
    @action(detail=True, methods=['get'])
    def edges(self, request, pk=None):
        """Get all edges (TA, TD, CA, CR) for a coordination run"""
        user_id = request.user.id if request.user else None
        run = self.get_object()
        
        logger.info("Coordination run edges request", extra={
            'user_id': user_id,
            'run_id': run.id,
            'algorithm': run.algorithm
        })
        
        try:
            # Get edges based on run's job
            ta_edges = TaEntry.objects.filter(job=run.job).select_related(
                'contributor', 'file'
            )
            td_edges = TdEdge.objects.filter(job=run.job).select_related(
                'file_a', 'file_b'
            )
            ca_edges = CaEdge.objects.filter(job=run.job).select_related(
                'contributor_i', 'contributor_j'
            )
            cr_edges = CrEdge.objects.filter(run=run).select_related(
                'contributor_i', 'contributor_j'
            )
            
            data = {
                'run_info': {
                    'id': run.id,
                    'algorithm': run.algorithm,
                    'score': float(run.score),
                    'cr_count': run.cr_count,
                    'diff_count': run.diff_count
                },
                'task_assignment': TaEntrySerializer(ta_edges, many=True).data,
                'technical_dependencies': TdEdgeSerializer(td_edges, many=True).data,
                'coordination_activities': CaEdgeSerializer(ca_edges, many=True).data,
                'coordination_requirements': CrEdgeSerializer(cr_edges, many=True).data,
                'statistics': {
                    'ta_edges_count': ta_edges.count(),
                    'td_edges_count': td_edges.count(),
                    'ca_edges_count': ca_edges.count(),
                    'cr_edges_count': cr_edges.count()
                }
            }
            
            logger.debug("Coordination run edges retrieved successfully", extra={
                'user_id': user_id,
                'run_id': run.id,
                'ta_count': ta_edges.count(),
                'cr_count': cr_edges.count()
            })
            
            return ApiResponse.success(
                data=data,
                message=f"Edges for coordination run {run.id} retrieved successfully"
            )
        except Exception as e:
            logger.error("Failed to retrieve coordination run edges", extra={
                'user_id': user_id,
                'run_id': run.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retrieve coordination run edges",
                error_code="COORDINATION_EDGES_ERROR"
            )

class TaEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for Task Assignment entries"""
    queryset = TaEntry.objects.select_related('job', 'contributor', 'file').all()
    serializer_class = TaEntrySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on job, contributor, and file parameters"""
        queryset = TaEntry.objects.select_related('job', 'contributor', 'file')
        
        job_id = self.request.query_params.get('job_id', '')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        
        contributor_id = self.request.query_params.get('contributor_id', '')
        if contributor_id:
            queryset = queryset.filter(contributor_id=contributor_id)
        
        return queryset.order_by('-edit_count')

class FunctionalClassViewSet(viewsets.ModelViewSet):
    """ViewSet for managing functional classes (DEV/SEC/OPS)"""
    queryset = FunctionalClass.objects.all()
    serializer_class = FunctionalClassSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on search parameters"""
        queryset = FunctionalClass.objects.all()
        
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('code')

class ContributorClassificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing contributor classifications"""
    queryset = ContributorClassification.objects.select_related(
        'project', 'contributor', 'class_ref', 'basis_job'
    ).all()
    serializer_class = ContributorClassificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on project and class parameters"""
        queryset = ContributorClassification.objects.select_related(
            'project', 'contributor', 'class_ref', 'basis_job'
        )
        
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        class_code = self.request.query_params.get('class_code', '')
        if class_code:
            queryset = queryset.filter(class_ref__code=class_code)
        
        return queryset.order_by('project_id', 'class_ref__code', 'contributor__github_login')

# Statistics and analysis endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def coordination_stats(request):
    """
    Get comprehensive coordination statistics.
    Returns aggregated data about coordination runs, algorithms, and scores.
    """
    user_id = request.user.id if request.user else None
    logger.info("Coordination statistics request", extra={
        'user_id': user_id
    })
    
    try:
        # Basic statistics
        total_runs = CoordinationRun.objects.count()
        projects_with_analysis = CoordinationRun.objects.values('project').distinct().count()
        
        # Algorithm usage statistics
        algorithm_stats = CoordinationRun.objects.values('algorithm').annotate(
            run_count=Count('id'),
            avg_score=Avg('score'),
            min_score=Min('score'),
            max_score=Max('score')
        ).order_by('-run_count')
        
        # Recent activity
        recent_runs = CoordinationRun.objects.select_related('project').order_by('-created_at')[:10]
        
        # Score distribution
        score_ranges = {
            'excellent': CoordinationRun.objects.filter(score__gte=0.8).count(),
            'good': CoordinationRun.objects.filter(score__gte=0.6, score__lt=0.8).count(),
            'moderate': CoordinationRun.objects.filter(score__gte=0.4, score__lt=0.6).count(),
            'poor': CoordinationRun.objects.filter(score__lt=0.4).count()
        }
        
        stats = {
            'total_runs': total_runs,
            'projects_analyzed': projects_with_analysis,
            'total_functional_classes': FunctionalClass.objects.count(),
            'total_classifications': ContributorClassification.objects.count(),
            'algorithm_statistics': list(algorithm_stats),
            'score_distribution': score_ranges,
            'recent_runs': CoordinationRunSerializer(recent_runs, many=True).data,
            'generated_at': timezone.now().isoformat()
        }
        
        logger.info("Coordination statistics retrieved successfully", extra={
            'user_id': user_id,
            'total_runs': total_runs,
            'projects_analyzed': projects_with_analysis
        })
        
        return ApiResponse.success(
            data=stats,
            message="Coordination statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve coordination statistics", extra={
            'user_id': user_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to retrieve coordination statistics",
            error_code="COORDINATION_STATS_ERROR"
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_coordination_analysis(request, project_id):
    """
    Get detailed coordination analysis for a specific project.
    Returns coordination runs, classification data, and trends.
    """
    user_id = request.user.id if request.user else None
    logger.info("Project coordination analysis request", extra={
        'user_id': user_id,
        'project_id': project_id
    })
    
    try:
        # Verify project exists
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            logger.warning("Project not found for coordination analysis", extra={
                'user_id': user_id,
                'project_id': project_id
            })
            return ApiResponse.not_found(
                error_message="Project not found",
                error_code="PROJECT_NOT_FOUND"
            )
        
        # Get coordination runs for this project
        coordination_runs = CoordinationRun.objects.filter(
            project_id=project_id
        ).select_related('job').order_by('-created_at')
        
        # Get contributor classifications
        classifications = ContributorClassification.objects.filter(
            project_id=project_id
        ).select_related('contributor', 'class_ref')
        
        # Get class distribution
        class_distribution = classifications.values(
            'class_ref__code', 'class_ref__name'
        ).annotate(
            contributor_count=Count('contributor')
        )
        
        # Calculate trends (if multiple runs exist)
        score_trend = list(coordination_runs.values('created_at', 'score', 'algorithm'))
        
        analysis = {
            'project': {
                'id': project.id,
                'name': project.name,
                'description': getattr(project, 'description', '')
            },
            'coordination_runs': CoordinationRunSerializer(coordination_runs, many=True).data,
            'contributor_classifications': ContributorClassificationSerializer(classifications, many=True).data,
            'class_distribution': list(class_distribution),
            'score_trends': score_trend,
            'summary': {
                'total_runs': coordination_runs.count(),
                'latest_score': coordination_runs.first().score if coordination_runs.exists() else None,
                'classified_contributors': classifications.count(),
                'analysis_date': timezone.now().isoformat()
            }
        }
        
        logger.info("Project coordination analysis completed successfully", extra={
            'user_id': user_id,
            'project_id': project_id,
            'runs_count': coordination_runs.count(),
            'classifications_count': classifications.count()
        })
        
        return ApiResponse.success(
            data=analysis,
            message=f"Coordination analysis for project {project.name} retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve project coordination analysis", extra={
            'user_id': user_id,
            'project_id': project_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to retrieve coordination analysis",
            error_code="PROJECT_COORDINATION_ANALYSIS_ERROR"
        )
