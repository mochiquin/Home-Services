import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import RiskAssessment, AlertRule, AlertEvent
from projects.models import Project
from coordination.models import CoordinationRun
from accounts.models import UserProfile
from rest_framework import serializers
from common.response import ApiResponse
from common.pagination import DefaultPagination

# Initialize logger for risks API
logger = logging.getLogger(__name__)

# Serializers
class RiskAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for RiskAssessment model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    run_algorithm = serializers.CharField(source='run.algorithm', read_only=True)
    run_score = serializers.DecimalField(source='run.score', max_digits=6, decimal_places=3, read_only=True)
    
    class Meta:
        model = RiskAssessment
        fields = ['id', 'project', 'project_name', 'run', 'run_algorithm', 'run_score',
                 'risk_type', 'risk_score', 'recommendation', 'created_at']
        read_only_fields = ['id', 'project_name', 'run_algorithm', 'run_score', 'created_at']

class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for AlertRule model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.display_name', read_only=True)
    events_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertRule
        fields = ['id', 'project', 'project_name', 'name', 'condition', 'severity',
                 'enabled', 'created_by', 'created_by_name', 'created_at', 'events_count']
        read_only_fields = ['id', 'project_name', 'created_by_name', 'created_at', 'events_count']
    
    def get_events_count(self, obj):
        return obj.events.count()

class AlertEventSerializer(serializers.ModelSerializer):
    """Serializer for AlertEvent model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    rule_severity = serializers.CharField(source='rule.severity', read_only=True)
    run_algorithm = serializers.CharField(source='run.algorithm', read_only=True)
    
    class Meta:
        model = AlertEvent
        fields = ['id', 'project', 'project_name', 'rule', 'rule_name', 'rule_severity',
                 'triggered_at', 'current_value', 'run', 'run_algorithm', 'status']
        read_only_fields = ['id', 'project_name', 'rule_name', 'rule_severity', 
                           'triggered_at', 'run_algorithm']

# ViewSets
class RiskAssessmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing risk assessments.
    Provides CRUD operations for risk analysis results.
    """
    queryset = RiskAssessment.objects.select_related('project', 'run').all()
    serializer_class = RiskAssessmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = RiskAssessment.objects.select_related('project', 'run')
        
        # Filter by project
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by risk type
        risk_type = self.request.query_params.get('risk_type', '')
        if risk_type:
            queryset = queryset.filter(risk_type__icontains=risk_type)
        
        # Filter by risk score range
        min_score = self.request.query_params.get('min_score', '')
        max_score = self.request.query_params.get('max_score', '')
        if min_score:
            queryset = queryset.filter(risk_score__gte=min_score)
        if max_score:
            queryset = queryset.filter(risk_score__lte=max_score)
        
        # Filter by severity level (high risk = high score)
        severity = self.request.query_params.get('severity', '')
        if severity == 'high':
            queryset = queryset.filter(risk_score__gte=0.7)
        elif severity == 'medium':
            queryset = queryset.filter(risk_score__gte=0.4, risk_score__lt=0.7)
        elif severity == 'low':
            queryset = queryset.filter(risk_score__lt=0.4)
        
        return queryset.order_by('-risk_score', '-created_at')
    
    def list(self, request, *args, **kwargs):
        """List risk assessments with logging"""
        user_id = request.user.id if request.user else None
        logger.info("Risk assessments list request", extra={
            'user_id': user_id,
            'project_id': request.query_params.get('project_id', ''),
            'risk_type': request.query_params.get('risk_type', ''),
            'severity': request.query_params.get('severity', '')
        })
        
        try:
            response = super().list(request, *args, **kwargs)
            logger.debug("Risk assessments list retrieved successfully", extra={
                'user_id': user_id,
                'count': response.data.get('count', 0) if hasattr(response, 'data') else 0
            })
            return response
        except Exception as e:
            logger.error("Failed to retrieve risk assessments list", extra={
                'user_id': user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retrieve risk assessments",
                error_code="RISK_ASSESSMENTS_LIST_ERROR"
            )

class AlertRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing alert rules.
    Provides CRUD operations for alert configuration.
    """
    queryset = AlertRule.objects.select_related('project', 'created_by').all()
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = AlertRule.objects.select_related('project', 'created_by')
        
        # Filter by project
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by enabled status
        enabled = self.request.query_params.get('enabled', '')
        if enabled in ['true', 'false']:
            queryset = queryset.filter(enabled=enabled.lower() == 'true')
        
        # Filter by severity
        severity = self.request.query_params.get('severity', '')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set the created_by field to current user's profile"""
        user_profile = getattr(self.request.user, 'profile', None)
        if user_profile:
            serializer.save(created_by=user_profile)
        else:
            # Create a profile if it doesn't exist
            user_profile = UserProfile.objects.create(user=self.request.user)
            serializer.save(created_by=user_profile)
    
    def create(self, request, *args, **kwargs):
        """Create new alert rule with logging"""
        user_id = request.user.id if request.user else None
        rule_name = request.data.get('name', '')
        project_id = request.data.get('project', '')
        
        logger.info("Creating new alert rule", extra={
            'user_id': user_id,
            'rule_name': rule_name,
            'project_id': project_id
        })
        
        try:
            response = super().create(request, *args, **kwargs)
            logger.info("Alert rule created successfully", extra={
                'user_id': user_id,
                'rule_name': rule_name,
                'rule_id': response.data.get('id') if hasattr(response, 'data') else None
            })
            return response
        except Exception as e:
            logger.error("Failed to create alert rule", extra={
                'user_id': user_id,
                'rule_name': rule_name,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to create alert rule",
                error_code="ALERT_RULE_CREATE_ERROR"
            )
    
    @action(detail=True, methods=['post'])
    def toggle_enabled(self, request, pk=None):
        """Toggle alert rule enabled status"""
        user_id = request.user.id if request.user else None
        rule = self.get_object()
        
        logger.info("Toggling alert rule status", extra={
            'user_id': user_id,
            'rule_id': rule.id,
            'rule_name': rule.name,
            'current_status': rule.enabled
        })
        
        try:
            old_status = rule.enabled
            rule.enabled = not rule.enabled
            rule.save()
            
            action = 'enabled' if rule.enabled else 'disabled'
            
            logger.info("Alert rule status changed successfully", extra={
                'user_id': user_id,
                'rule_id': rule.id,
                'rule_name': rule.name,
                'old_status': old_status,
                'new_status': rule.enabled,
                'action': action
            })
            
            return ApiResponse.success(
                data={'enabled': rule.enabled},
                message=f'Alert rule "{rule.name}" has been {action}'
            )
        except Exception as e:
            logger.error("Failed to toggle alert rule status", extra={
                'user_id': user_id,
                'rule_id': rule.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to toggle alert rule status",
                error_code="ALERT_RULE_TOGGLE_ERROR"
            )

class AlertEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing alert events.
    Provides operations for alert event lifecycle management.
    """
    queryset = AlertEvent.objects.select_related('project', 'rule', 'run').all()
    serializer_class = AlertEventSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = AlertEvent.objects.select_related('project', 'rule', 'run')
        
        # Filter by project
        project_id = self.request.query_params.get('project_id', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by severity (via rule)
        severity = self.request.query_params.get('severity', '')
        if severity:
            queryset = queryset.filter(rule__severity=severity)
        
        # Filter by date range
        days = self.request.query_params.get('days', '')
        if days:
            try:
                days_int = int(days)
                since_date = timezone.now() - timezone.timedelta(days=days_int)
                queryset = queryset.filter(triggered_at__gte=since_date)
            except ValueError:
                pass
        
        return queryset.order_by('-triggered_at')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert event"""
        user_id = request.user.id if request.user else None
        event = self.get_object()
        
        logger.info("Acknowledging alert event", extra={
            'user_id': user_id,
            'event_id': event.id,
            'rule_name': event.rule.name,
            'current_status': event.status
        })
        
        try:
            if event.status != AlertEvent.Status.OPEN:
                logger.warning("Attempted to acknowledge non-open alert event", extra={
                    'user_id': user_id,
                    'event_id': event.id,
                    'current_status': event.status
                })
                return ApiResponse.error(
                    error_message=f"Cannot acknowledge event with status: {event.status}",
                    error_code="INVALID_EVENT_STATUS"
                )
            
            event.status = AlertEvent.Status.ACK
            event.save()
            
            logger.info("Alert event acknowledged successfully", extra={
                'user_id': user_id,
                'event_id': event.id,
                'rule_name': event.rule.name
            })
            
            return ApiResponse.success(
                data={'status': event.status},
                message=f'Alert event for rule "{event.rule.name}" has been acknowledged'
            )
        except Exception as e:
            logger.error("Failed to acknowledge alert event", extra={
                'user_id': user_id,
                'event_id': event.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to acknowledge alert event",
                error_code="ALERT_ACK_ERROR"
            )
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an alert event"""
        user_id = request.user.id if request.user else None
        event = self.get_object()
        
        logger.info("Closing alert event", extra={
            'user_id': user_id,
            'event_id': event.id,
            'rule_name': event.rule.name,
            'current_status': event.status
        })
        
        try:
            if event.status == AlertEvent.Status.CLOSED:
                logger.warning("Attempted to close already closed alert event", extra={
                    'user_id': user_id,
                    'event_id': event.id
                })
                return ApiResponse.error(
                    error_message="Alert event is already closed",
                    error_code="ALREADY_CLOSED"
                )
            
            event.status = AlertEvent.Status.CLOSED
            event.save()
            
            logger.info("Alert event closed successfully", extra={
                'user_id': user_id,
                'event_id': event.id,
                'rule_name': event.rule.name
            })
            
            return ApiResponse.success(
                data={'status': event.status},
                message=f'Alert event for rule "{event.rule.name}" has been closed'
            )
        except Exception as e:
            logger.error("Failed to close alert event", extra={
                'user_id': user_id,
                'event_id': event.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to close alert event",
                error_code="ALERT_CLOSE_ERROR"
            )

# Statistics and analysis endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def risk_stats(request):
    """
    Get comprehensive risk statistics.
    Returns aggregated data about risk assessments, alerts, and trends.
    """
    user_id = request.user.id if request.user else None
    logger.info("Risk statistics request", extra={
        'user_id': user_id
    })
    
    try:
        # Risk assessment statistics
        total_assessments = RiskAssessment.objects.count()
        high_risk_count = RiskAssessment.objects.filter(risk_score__gte=0.7).count()
        
        # Risk type distribution
        risk_type_stats = RiskAssessment.objects.values('risk_type').annotate(
            count=Count('id'),
            avg_score=Avg('risk_score'),
            max_score=Max('risk_score')
        ).order_by('-count')
        
        # Alert statistics
        total_rules = AlertRule.objects.count()
        active_rules = AlertRule.objects.filter(enabled=True).count()
        total_events = AlertEvent.objects.count()
        open_events = AlertEvent.objects.filter(status=AlertEvent.Status.OPEN).count()
        
        # Alert severity distribution
        severity_stats = AlertEvent.objects.values('rule__severity').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Recent high-risk assessments
        recent_high_risks = RiskAssessment.objects.filter(
            risk_score__gte=0.7
        ).select_related('project', 'run').order_by('-created_at')[:10]
        
        stats = {
            'risk_assessments': {
                'total': total_assessments,
                'high_risk': high_risk_count,
                'high_risk_percentage': (high_risk_count / total_assessments * 100) if total_assessments > 0 else 0,
                'by_type': list(risk_type_stats)
            },
            'alert_system': {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'total_events': total_events,
                'open_events': open_events,
                'by_severity': list(severity_stats)
            },
            'recent_high_risks': RiskAssessmentSerializer(recent_high_risks, many=True).data,
            'generated_at': timezone.now().isoformat()
        }
        
        logger.info("Risk statistics retrieved successfully", extra={
            'user_id': user_id,
            'total_assessments': total_assessments,
            'high_risk_count': high_risk_count,
            'open_events': open_events
        })
        
        return ApiResponse.success(
            data=stats,
            message="Risk statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve risk statistics", extra={
            'user_id': user_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to retrieve risk statistics",
            error_code="RISK_STATS_ERROR"
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_risk_analysis(request, project_id):
    """
    Get detailed risk analysis for a specific project.
    Returns risk assessments, alert rules, events, and trends.
    """
    user_id = request.user.id if request.user else None
    logger.info("Project risk analysis request", extra={
        'user_id': user_id,
        'project_id': project_id
    })
    
    try:
        # Verify project exists
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            logger.warning("Project not found for risk analysis", extra={
                'user_id': user_id,
                'project_id': project_id
            })
            return ApiResponse.not_found(
                error_message="Project not found",
                error_code="PROJECT_NOT_FOUND"
            )
        
        # Get risk assessments for this project
        risk_assessments = RiskAssessment.objects.filter(
            project_id=project_id
        ).select_related('run').order_by('-created_at')
        
        # Get alert rules and events
        alert_rules = AlertRule.objects.filter(
            project_id=project_id
        ).select_related('created_by')
        
        alert_events = AlertEvent.objects.filter(
            project_id=project_id
        ).select_related('rule', 'run').order_by('-triggered_at')
        
        # Calculate risk trends
        risk_trend = list(risk_assessments.values(
            'created_at', 'risk_type', 'risk_score'
        ))
        
        # Get current risk summary
        current_risks = risk_assessments.values('risk_type').annotate(
            latest_score=Max('risk_score'),
            assessment_count=Count('id')
        )
        
        analysis = {
            'project': {
                'id': project.id,
                'name': project.name,
                'description': getattr(project, 'description', '')
            },
            'risk_assessments': RiskAssessmentSerializer(risk_assessments, many=True).data,
            'alert_rules': AlertRuleSerializer(alert_rules, many=True).data,
            'alert_events': AlertEventSerializer(alert_events, many=True).data,
            'risk_trends': risk_trend,
            'current_risk_summary': list(current_risks),
            'summary': {
                'total_assessments': risk_assessments.count(),
                'high_risk_assessments': risk_assessments.filter(risk_score__gte=0.7).count(),
                'active_alert_rules': alert_rules.filter(enabled=True).count(),
                'open_alert_events': alert_events.filter(status=AlertEvent.Status.OPEN).count(),
                'analysis_date': timezone.now().isoformat()
            }
        }
        
        logger.info("Project risk analysis completed successfully", extra={
            'user_id': user_id,
            'project_id': project_id,
            'assessments_count': risk_assessments.count(),
            'alert_rules_count': alert_rules.count(),
            'alert_events_count': alert_events.count()
        })
        
        return ApiResponse.success(
            data=analysis,
            message=f"Risk analysis for project {project.name} retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve project risk analysis", extra={
            'user_id': user_id,
            'project_id': project_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Failed to retrieve risk analysis",
            error_code="PROJECT_RISK_ANALYSIS_ERROR"
        )
