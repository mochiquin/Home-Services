from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'members', views.ProjectMemberViewSet, basename='projectmember')

urlpatterns = [
    # Project management API routes
    path('', include(router.urls)),
]

