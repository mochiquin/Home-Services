from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.login_view, name='auth_login'),
    path('auth/register/', views.register_view, name='auth_register'),
    path('auth/logout/', views.logout_view, name='auth_logout'),
    
    # Admin statistics (staff only)
    path('admin/stats/', views.user_stats, name='user_stats'),
    
    # Health check endpoint
    path('health/', views.health_check, name='health_check'),
    
    # User management API routes
    path('', include(router.urls)),
]
