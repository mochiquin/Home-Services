from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import UserProfile
from .serializers import (
    UserSerializer, UserDetailSerializer, UserProfileSerializer, 
    UserRegistrationSerializer, PasswordChangeSerializer, UserUpdateSerializer,
    UserProfileUpdateSerializer
)
from .services import UserProfileService, UserService

# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint using service layer.
    Accepts email/password and returns JWT tokens with user information.
    """
    try:
        # Use service layer for authentication
        auth_result = UserService.authenticate_user(
            request.data.get('email'),
            request.data.get('password')
        )
        
        # Generate tokens
        tokens = UserService.generate_tokens(auth_result['user'])
        
        return Response({
            'refresh': tokens['refresh'],
            'access': tokens['access'],
            'user': UserDetailSerializer(auth_result['user']).data,
            'message': auth_result['message']
        })
        
    except ValidationError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({
            'error': 'Login failed',
            'details': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint using service layer.
    Creates a new user account and returns JWT tokens.
    """
    try:
        # Use service layer for registration
        result = UserService.register_user(request.data)
        
        return Response({
            'refresh': result['tokens']['refresh'],
            'access': result['tokens']['access'],
            'user': UserDetailSerializer(result['user']).data,
            'message': result['message']
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'error': 'Registration failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Registration failed',
            'details': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint using service layer.
    Blacklists the provided refresh token.
    """
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use service layer for logout
        result = UserService.logout_user(refresh_token)
        
        return Response({
            'message': result['message']
        })
        
    except ValidationError as e:
        return Response({
            'error': 'Logout failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Logout failed',
            'details': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.
    Provides CRUD operations for user accounts with proper permissions.
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['retrieve', 'list']:
            return UserDetailSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users can only see themselves, staff can see all active users.
        """
        queryset = User.objects.filter(is_active=True)
        
        # Non-staff users can only see themselves
        if not self.request.user.is_staff:
            queryset = queryset.filter(id=self.request.user.id)
        
        # Search functionality
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset.order_by('-date_joined')
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user information using service layer"""
        try:
            # Use service layer to get user details
            result = UserService.get_user_detail(request.user)
            
            return Response(UserDetailSerializer(result['user']).data)
            
        except Exception as e:
            return Response({
                'error': 'Failed to get user information',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """
        Update current user profile information using service layer.
        Only allows updating contact_email, first_name, and last_name.
        display_name is auto-generated from first_name + last_name.
        """
        try:
            # Validate input data
            serializer = UserProfileUpdateSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response({
                    'error': 'Profile data validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer for business logic
            result = UserProfileService.update_user_profile(
                request.user, 
                serializer.validated_data
            )
            
            # Return updated user information
            return Response({
                'user': UserDetailSerializer(result['user']).data,
                'message': result['message']
            })
            
        except ValidationError as e:
            return Response({
                'error': 'Profile update failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Internal server error',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password using service layer"""
        try:
            # Validate input data
            serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
            if not serializer.is_valid():
                return Response({
                    'error': 'Password change validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer for password change
            result = UserService.change_password(
                request.user,
                serializer.validated_data['old_password'],
                serializer.validated_data['new_password']
            )
            
            return Response({
                'message': result['message']
            })
            
        except ValidationError as e:
            return Response({
                'error': 'Password change failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Password change failed',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def toggle_active(self, request, pk=None):
        """
        Activate/deactivate user account.
        Only accessible by admin users.
        """
        user = self.get_object()
        if user == request.user:
            return Response({
                'error': 'Cannot deactivate your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = not user.is_active
        user.save()
        
        action = 'activated' if user.is_active else 'deactivated'
        return Response({
            'message': f'User {user.username} has been {action}',
            'is_active': user.is_active
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """
    Get user statistics using service layer.
    Only accessible by staff members.
    """
    if not request.user.is_staff:
        return Response({
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Use service layer to get user statistics
        result = UserService.get_user_stats()
        
        # Add additional stats for admin view
        stats = {
            'total_users': result['total_users'],
            'active_users': result['active_users'],
            'inactive_users': User.objects.filter(is_active=False).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'recent_users': result['recent_users'],
        }
        
        return Response(stats)
        
    except Exception as e:
        return Response({
            'error': 'Failed to get user statistics',
            'details': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    API health check endpoint.
    Returns system status and version information.
    """
    return Response({
        'status': 'healthy',
        'message': 'Secuflow User Management API is running',
        'version': '1.0.0'
    })