from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'coordination-runs', views.CoordinationRunViewSet)
router.register(r'task-assignments', views.TaEntryViewSet)
router.register(r'functional-classes', views.FunctionalClassViewSet)
router.register(r'contributor-classifications', views.ContributorClassificationViewSet)

# URL patterns
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional function-based views
    path('stats/', views.coordination_stats, name='coordination-stats'),
    path('projects/<int:project_id>/analysis/', views.project_coordination_analysis, name='project-coordination-analysis'),
]
