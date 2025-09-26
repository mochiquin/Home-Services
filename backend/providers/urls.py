from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'providers', views.ServiceProviderViewSet, basename='serviceprovider')
router.register(r'services', views.ProviderServiceViewSet, basename='providerservice')

urlpatterns = [
    # Service Providers API routes
    path('', include(router.urls)),
]