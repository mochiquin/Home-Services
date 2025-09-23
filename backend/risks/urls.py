from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'risk-assessments', views.RiskAssessmentViewSet)
router.register(r'alert-rules', views.AlertRuleViewSet)
router.register(r'alert-events', views.AlertEventViewSet)

# URL patterns
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional function-based views
    path('stats/', views.risk_stats, name='risk-stats'),
    path('projects/<int:project_id>/analysis/', views.project_risk_analysis, name='project-risk-analysis'),
]
