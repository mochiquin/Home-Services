from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'contributors', views.ContributorViewSet)
router.register(r'project-contributors', views.ProjectContributorViewSet)
router.register(r'code-files', views.CodeFileViewSet)
router.register(r'commits', views.CommitViewSet)

# URL patterns
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional function-based views
    path('stats/', views.contributor_stats, name='contributor-stats'),
    path('projects/<int:project_id>/analysis/', views.project_contributor_analysis, name='project-contributor-analysis'),
    
    # TNM Analysis and Classification APIs
    path('projects/<uuid:project_id>/analyze_tnm/', views.analyze_tnm_contributors, name='analyze-tnm-contributors'),
    path('projects/<uuid:project_id>/classification/', views.project_contributors_classification, name='project-contributors-classification'),
    path('functional-role-choices/', views.functional_role_choices, name='functional-role-choices'),
]
