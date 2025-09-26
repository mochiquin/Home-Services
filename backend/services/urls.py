from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'categories', views.ServiceCategoryViewSet, basename='servicecategory')
router.register(r'services', views.ServiceViewSet, basename='service')
router.register(r'areas', views.ServiceAreaViewSet, basename='servicearea')

urlpatterns = [
    # Home Services API routes
    path('', include(router.urls)),
]