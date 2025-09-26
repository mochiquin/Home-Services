import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import UserProfile
from .serializers import (
    UserSerializer, UserProfileSerializer, RegisterSerializer, LoginSerializer
)
from .services import UserProfileService, UserService
from common.response import ApiResponse

# Initialize logger for accounts API
logger = logging.getLogger(__name__)

# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint using service layer.
    Accepts email/password and returns JWT tokens with user information.
    """
    email = request.data.get('email')
    logger.info("User login attempt", extra={
        'email': email,
        'ip_address': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', '')
    })
    
    try:
        # Use service layer for authentication
        auth_result = UserService.authenticate_user(email, request.data.get('password'))
        
        # Generate tokens
        tokens = UserService.generate_tokens(auth_result['user'])
        
        logger.info("User login successful", extra={
            'user_id': auth_result['user'].id,
            'email': email,
            'ip_address': request.META.get('REMOTE_ADDR')
        })
        
        return ApiResponse.success(
            data={
                'refresh': tokens['refresh'],
                'access': tokens['access'],
                'user': UserSerializer(auth_result['user']).data
            },
            message=auth_result['message']
        )
        
    except ValidationError as e:
        logger.warning("User login failed - invalid credentials", extra={
            'email': email,
            'error': str(e),
            'ip_address': request.META.get('REMOTE_ADDR')
        })
        return ApiResponse.unauthorized(
            error_message=str(e),
            error_code="INVALID_CREDENTIALS"
        )
    except Exception as e:
        logger.error("User login failed - system error", extra={
            'email': email,
            'error': str(e),
            'ip_address': request.META.get('REMOTE_ADDR')
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Login failed",
            error_code="LOGIN_ERROR"
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint using service layer.
    Creates a new user account and returns JWT tokens.
    """
    email = request.data.get('email')
    username = request.data.get('username')
    logger.info("User registration attempt", extra={
        'email': email,
        'username': username,
        'ip_address': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', '')
    })
    
    try:
        # Use service layer for registration
        result = UserService.register_user(request.data)
        
        logger.info("User registration successful", extra={
            'user_id': result['user'].id,
            'email': email,
            'username': username,
            'ip_address': request.META.get('REMOTE_ADDR')
        })
        
        return ApiResponse.created(
            data={
                'refresh': result['tokens']['refresh'],
                'access': result['tokens']['access'],
                'user': UserSerializer(result['user']).data
            },
            message=result['message']
        )
        
    except ValidationError as e:
        logger.warning("User registration failed - validation error", extra={
            'email': email,
            'username': username,
            'error': str(e),
            'ip_address': request.META.get('REMOTE_ADDR')
        })
        return ApiResponse.error(
            error_message=str(e),
            error_code="REGISTRATION_ERROR"
        )
    except Exception as e:
        logger.error("User registration failed - system error", extra={
            'email': email,
            'username': username,
            'error': str(e),
            'ip_address': request.META.get('REMOTE_ADDR')
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Registration failed",
            error_code="REGISTRATION_ERROR"
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint using service layer.
    Blacklists the provided refresh token.
    """
    user_id = request.user.id if request.user else None
    logger.info("User logout attempt", extra={
        'user_id': user_id,
        'ip_address': request.META.get('REMOTE_ADDR')
    })
    
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            logger.warning("Logout failed - missing refresh token", extra={
                'user_id': user_id
            })
            return ApiResponse.error(
                error_message="Refresh token is required",
                error_code="MISSING_TOKEN"
            )
        
        # Use service layer for logout
        result = UserService.logout_user(refresh_token)
        
        logger.info("User logout successful", extra={
            'user_id': user_id,
            'ip_address': request.META.get('REMOTE_ADDR')
        })
        
        return ApiResponse.success(
            message=result['message']
        )
        
    except ValidationError as e:
        logger.warning("User logout failed - validation error", extra={
            'user_id': user_id,
            'error': str(e)
        })
        return ApiResponse.error(
            error_message=str(e),
            error_code="LOGOUT_ERROR"
        )
    except Exception as e:
        logger.error("User logout failed - system error", extra={
            'user_id': user_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message="Logout failed",
            error_code="LOGOUT_ERROR"
        )

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
            return UserSerializer
        elif self.action in ['update', 'partial_update']:
            return UserSerializer
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
    
    def list(self, request, *args, **kwargs):
        """Get user list with ApiResponse format and proper logging"""
        user_id = request.user.id if request.user else None
        search = request.query_params.get('search', '')
        
        logger.info("User list request", extra={
            'user_id': user_id,
            'search': search,
            'is_staff': request.user.is_staff if request.user else False
        })
        
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                # Build paginated response manually using ApiResponse
                paginator = self.paginator
                return ApiResponse.success(data={
                    'results': serializer.data,
                    'count': paginator.page.paginator.count,
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link()
                }, message="User list retrieved successfully")
            
            serializer = self.get_serializer(queryset, many=True)
            logger.debug("User list retrieved successfully", extra={
                'user_id': user_id,
                'users_count': len(serializer.data)
            })
            
            return ApiResponse.success(
                data=serializer.data,
                message="User list retrieved successfully"
            )
            
        except Exception as e:
            logger.error("Failed to retrieve user list", extra={
                'user_id': user_id,
                'search': search,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to get user list",
                error_code="USER_LIST_ERROR"
            )
    
    def retrieve(self, request, *args, **kwargs):
        """Get user details by ID using service layer and ApiResponse format"""
        user_id = request.user.id if request.user else None
        target_user_id = kwargs.get('pk')
        
        logger.info("User details request", extra={
            'user_id': user_id,
            'target_user_id': target_user_id,
            'action': 'get_user_details'
        })
        
        try:
            # Get the target user object
            instance = self.get_object()
            
            # Use service layer to get user details
            result = UserService.get_user_detail(instance)
            
            logger.debug("User details retrieved successfully", extra={
                'user_id': user_id,
                'target_user_id': target_user_id
            })
            
            return ApiResponse.success(
                data=UserDetailSerializer(result['user']).data,
                message="User details retrieved successfully"
            )
            
        except Exception as e:
            logger.error("Failed to retrieve user details", extra={
                'user_id': user_id,
                'target_user_id': target_user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to get user details",
                error_code="USER_DETAILS_ERROR"
            )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user information using service layer"""
        user_id = request.user.id if request.user else None
        logger.info("User profile request", extra={
            'user_id': user_id,
            'action': 'get_profile'
        })
        
        try:
            # Use service layer to get user details
            result = UserService.get_user_detail(request.user)
            
            logger.debug("User profile retrieved successfully", extra={
                'user_id': user_id
            })
            
            return ApiResponse.success(
                data=UserSerializer(result['user']).data,
                message="User information retrieved successfully"
            )
            
        except Exception as e:
            logger.error("Failed to retrieve user profile", extra={
                'user_id': user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to get user information",
                error_code="USER_INFO_ERROR"
            )
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """
        Update current user profile information using service layer.
        Only allows updating contact_email, first_name, and last_name.
        display_name is auto-generated from first_name + last_name.
        """
        user_id = request.user.id if request.user else None
        logger.info("User profile update attempt", extra={
            'user_id': user_id,
            'fields_to_update': list(request.data.keys()) if request.data else []
        })
        
        try:
            # Validate input data
            serializer = UserProfileSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                logger.warning("Profile update failed - validation error", extra={
                    'user_id': user_id,
                    'validation_errors': serializer.errors
                })
                return ApiResponse.error(
                    error_message="Profile data validation failed",
                    error_code="VALIDATION_ERROR",
                    data=serializer.errors
                )
            
            # Use service layer for business logic
            result = UserProfileService.update_user_profile(
                request.user, 
                serializer.validated_data
            )
            
            logger.info("User profile updated successfully", extra={
                'user_id': user_id,
                'updated_fields': list(serializer.validated_data.keys())
            })
            
            # Return updated user information
            return ApiResponse.success(
                data={
                    'user': UserSerializer(result['user']).data
                },
                message=result['message']
            )
            
        except ValidationError as e:
            logger.warning("Profile update failed - business validation error", extra={
                'user_id': user_id,
                'error': str(e)
            })
            return ApiResponse.error(
                error_message=str(e),
                error_code="PROFILE_UPDATE_ERROR"
            )
        except Exception as e:
            logger.error("Profile update failed - system error", extra={
                'user_id': user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Profile update failed",
                error_code="PROFILE_UPDATE_ERROR"
            )
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password using service layer"""
        user_id = request.user.id if request.user else None
        logger.info("Password change attempt", extra={
            'user_id': user_id,
            'ip_address': request.META.get('REMOTE_ADDR')
        })
        
        try:
            # Validate input data
            # 简化的密码验证逻辑
            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')
            
            if not old_password or not new_password:
                return ApiResponse.error(
                    error_message="Both old_password and new_password are required",
                    error_code='PASSWORD_CHANGE_ERROR',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Use service layer for password change
            result = UserService.change_password(
                request.user,
                old_password,
                new_password
            )
            
            logger.info("Password changed successfully", extra={
                'user_id': user_id,
                'ip_address': request.META.get('REMOTE_ADDR')
            })
            
            return ApiResponse.success(
                message=result['message']
            )
            
        except ValidationError as e:
            logger.warning("Password change failed - business validation error", extra={
                'user_id': user_id,
                'error': str(e)
            })
            return ApiResponse.error(
                error_message=str(e),
                error_code="PASSWORD_CHANGE_ERROR"
            )
        except Exception as e:
            logger.error("Password change failed - system error", extra={
                'user_id': user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Password change failed",
                error_code="PASSWORD_CHANGE_ERROR"
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def toggle_active(self, request, pk=None):
        """
        Activate/deactivate user account.
        Only accessible by admin users.
        """
        admin_user_id = request.user.id if request.user else None
        target_user = self.get_object()
        
        logger.info("Admin user account toggle attempt", extra={
            'admin_user_id': admin_user_id,
            'target_user_id': target_user.id,
            'target_username': target_user.username,
            'current_status': target_user.is_active
        })
        
        if target_user == request.user:
            logger.warning("Admin attempted to deactivate own account", extra={
                'admin_user_id': admin_user_id
            })
            return ApiResponse.error(
                error_message='Cannot deactivate your own account',
                error_code="SELF_DEACTIVATION_ERROR"
            )
        
        # Toggle active status
        old_status = target_user.is_active
        target_user.is_active = not target_user.is_active
        target_user.save()
        
        action = 'activated' if target_user.is_active else 'deactivated'
        
        logger.info("User account status changed successfully", extra={
            'admin_user_id': admin_user_id,
            'target_user_id': target_user.id,
            'target_username': target_user.username,
            'old_status': old_status,
            'new_status': target_user.is_active,
            'action': action
        })
        
        return ApiResponse.success(
            data={'is_active': target_user.is_active},
            message=f'User {target_user.username} has been {action}'
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """
    Get user statistics using service layer.
    Only accessible by staff members.
    """
    user_id = request.user.id if request.user else None
    logger.info("User statistics request", extra={
        'user_id': user_id,
        'is_staff': request.user.is_staff if request.user else False
    })
    
    if not request.user.is_staff:
        logger.warning("Non-staff user attempted to access user statistics", extra={
            'user_id': user_id
        })
        return ApiResponse.forbidden(
            error_message='Permission denied - staff access required',
            error_code="INSUFFICIENT_PERMISSIONS"
        )
    
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
        
        logger.info("User statistics retrieved successfully", extra={
            'admin_user_id': user_id,
            'total_users': stats['total_users'],
            'active_users': stats['active_users']
        })
        
        return ApiResponse.success(
            data=stats,
            message="User statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve user statistics", extra={
            'admin_user_id': user_id,
            'error': str(e)
        }, exc_info=True)
        return ApiResponse.internal_error(
            error_message='Failed to get user statistics',
            error_code="USER_STATS_ERROR"
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    API health check endpoint.
    Returns system status and version information.
    """
    logger.debug("Health check request", extra={
        'ip_address': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', '')
    })
    
    return ApiResponse.success(
        data={
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': timezone.now().isoformat()
        },
        message='Secuflow User Management API is running'
    )