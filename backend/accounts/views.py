from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from .models import UserProfile
from .serializers import (
    UserSerializer, UserDetailSerializer, UserProfileSerializer, 
    UserRegistrationSerializer, PasswordChangeSerializer, UserUpdateSerializer
)

# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint.
    Accepts username/password and returns JWT tokens with user information.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    if user and user.is_active:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserDetailSerializer(user).data,
            'message': 'Login successful'
        })
    else:
        return Response({
            'error': 'Invalid credentials or account is disabled'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint.
    Creates a new user account and returns JWT tokens.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserDetailSerializer(user).data,
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)
    return Response({
        'error': 'Registration failed',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint.
    Blacklists the provided refresh token.
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Logout successful'})
    except Exception as e:
        return Response({
            'error': 'Logout failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

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
        """Get current user information"""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """
        Update current user profile information.
        Handles both user basic info and profile data.
        """
        user = request.user
        user_data = {}
        profile_data = {}
        
        # Separate user data from profile data
        user_fields = ['first_name', 'last_name', 'email']
        profile_fields = ['phone', 'bio', 'avatar']
        
        for field in user_fields:
            if field in request.data:
                user_data[field] = request.data[field]
        
        for field in profile_fields:
            if field in request.data:
                profile_data[field] = request.data[field]
        
        # Update user basic information
        if user_data:
            user_serializer = UserUpdateSerializer(user, data=user_data, partial=True)
            if not user_serializer.is_valid():
                return Response({
                    'error': 'User data validation failed',
                    'details': user_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            user_serializer.save()
        
        # Update user profile
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile_serializer = UserProfileSerializer(profile, data=profile_data, partial=True)
            if not profile_serializer.is_valid():
                return Response({
                    'error': 'Profile data validation failed',
                    'details': profile_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            profile_serializer.save()
        
        # Return updated user information
        updated_user = User.objects.get(id=user.id)
        return Response({
            'user': UserDetailSerializer(updated_user).data,
            'message': 'Profile updated successfully'
        })
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password with old password verification"""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response({
            'error': 'Password change failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
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
    Get user statistics.
    Only accessible by staff members.
    """
    if not request.user.is_staff:
        return Response({
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
        'recent_users': User.objects.filter(
            date_joined__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
    }
    
    return Response(stats)

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