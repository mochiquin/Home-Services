"""
User service layer for handling all user-related business logic.
Separates business logic from views and serializers.
"""
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile


class UserProfileService:
    """Service class for user profile operations."""
    
    @staticmethod
    def get_or_create_profile(user):
        """
        Get or create user profile.
        
        Args:
            user: Django User instance
            
        Returns:
            UserProfile instance
        """
        profile, created = UserProfile.objects.get_or_create(user=user)
        return profile
    
    @staticmethod
    def update_user_basic_info(user, first_name=None, last_name=None):
        """
        Update user's basic information (first_name, last_name).
        
        Args:
            user: Django User instance
            first_name: User's first name (optional)
            last_name: User's last name (optional)
            
        Returns:
            Updated User instance
        """
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        
        user.save()
        return user
    
    @staticmethod
    def update_profile_info(profile, contact_email=None):
        """
        Update user profile information.
        
        Args:
            profile: UserProfile instance
            contact_email: Contact email (optional)
            
        Returns:
            Updated UserProfile instance
        """
        if contact_email is not None:
            profile.contact_email = contact_email
        
        # Save profile (this will trigger display_name auto-generation)
        profile.save()
        return profile
    
    @staticmethod
    @transaction.atomic
    def update_user_profile(user, profile_data):
        """
        Update complete user profile with transaction management.
        
        Args:
            user: Django User instance
            profile_data: Dictionary containing profile update data
            
        Returns:
            Dictionary with updated user and profile information
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Extract data
            first_name = profile_data.get('first_name')
            last_name = profile_data.get('last_name')
            contact_email = profile_data.get('contact_email')
            
            # Get or create profile
            profile = UserProfileService.get_or_create_profile(user)
            
            # Update user basic info
            if first_name is not None or last_name is not None:
                UserProfileService.update_user_basic_info(
                    user, 
                    first_name=first_name, 
                    last_name=last_name
                )
            
            # Update profile info
            if contact_email is not None:
                UserProfileService.update_profile_info(
                    profile, 
                    contact_email=contact_email
                )
            
            # Refresh user from database to get updated data
            user.refresh_from_db()
            profile.refresh_from_db()
            
            return {
                'user': user,
                'profile': profile,
                'success': True,
                'message': 'Profile updated successfully'
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to update profile: {str(e)}")
    
    @staticmethod
    def get_user_profile_data(user):
        """
        Get complete user profile data.
        
        Args:
            user: Django User instance
            
        Returns:
            Dictionary with user and profile data
        """
        profile = UserProfileService.get_or_create_profile(user)
        
        return {
            'user': user,
            'profile': profile,
            'display_name': profile.display_name,
            'contact_email': profile.contact_email
        }


class UserService:
    """Service class for all user-related operations."""
    
    @staticmethod
    def authenticate_user(email, password):
        """
        Authenticate user by email and password.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dictionary with authentication result
        """
        if not email or not password:
            raise ValidationError("Email and password are required")
        
        # Resolve username by email for authentication
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            raise ValidationError("Invalid email or password")
        
        user = authenticate(username=username, password=password)
        if not user:
            raise ValidationError("Invalid email or password")
        
        if not user.is_active:
            raise ValidationError("Account is disabled")
        
        return {
            'user': user,
            'success': True,
            'message': 'Authentication successful'
        }
    
    @staticmethod
    def generate_tokens(user):
        """
        Generate JWT tokens for user.
        
        Args:
            user: Django User instance
            
        Returns:
            Dictionary with tokens
        """
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }
    
    @staticmethod
    @transaction.atomic
    def register_user(user_data):
        """
        Register a new user.
        
        Args:
            user_data: Dictionary containing user registration data
            
        Returns:
            Dictionary with registration result
        """
        from .serializers import UserRegistrationSerializer
        
        # Validate registration data
        serializer = UserRegistrationSerializer(data=user_data)
        if not serializer.is_valid():
            raise ValidationError(f"Registration validation failed: {serializer.errors}")
        
        # Create user
        user = serializer.save()
        
        # Generate tokens
        tokens = UserService.generate_tokens(user)
        
        return {
            'user': user,
            'tokens': tokens,
            'success': True,
            'message': 'Registration successful'
        }
    
    @staticmethod
    def logout_user(refresh_token):
        """
        Logout user by blacklisting refresh token.
        
        Args:
            refresh_token: JWT refresh token string
            
        Returns:
            Dictionary with logout result
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return {
                'success': True,
                'message': 'Logout successful'
            }
        except Exception as e:
            raise ValidationError(f"Logout failed: {str(e)}")
    
    @staticmethod
    def get_user_detail(user):
        """
        Get detailed user information.
        
        Args:
            user: Django User instance
            
        Returns:
            Dictionary with user details
        """
        return {
            'user': user,
            'profile': UserProfileService.get_or_create_profile(user),
            'success': True
        }
    
    @staticmethod
    def change_password(user, old_password, new_password):
        """
        Change user password with old password verification.
        
        Args:
            user: Django User instance
            old_password: Current password
            new_password: New password
            
        Returns:
            Dictionary with password change result
        """
        if not user.check_password(old_password):
            raise ValidationError("Current password is incorrect")
        
        if len(new_password) < 8:
            raise ValidationError("New password must be at least 8 characters long")
        
        user.set_password(new_password)
        user.save()
        
        return {
            'success': True,
            'message': 'Password changed successfully'
        }
    
    @staticmethod
    def get_user_stats():
        """
        Get user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        recent_users = User.objects.filter(
            date_joined__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'recent_users': recent_users,
            'success': True
        }
    
    @staticmethod
    def search_users(query, user=None):
        """
        Search users by various criteria.
        
        Args:
            query: Search query string
            user: Current user (for permission checks)
            
        Returns:
            Dictionary with search results
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError("Search query must be at least 2 characters long")
        
        # Build search query
        search_query = Q(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(profile__display_name__icontains=query)
        )
        
        users = User.objects.filter(search_query).select_related('profile')[:20]
        
        return {
            'users': users,
            'count': users.count(),
            'success': True
        }
    
    @staticmethod
    def get_user_by_id(user_id):
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User instance
        """
        try:
            return User.objects.select_related('profile').get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError("User not found")
    
    @staticmethod
    def update_user_basic_info(user, user_data):
        """
        Update user's basic information.
        
        Args:
            user: Django User instance
            user_data: Dictionary containing user data
            
        Returns:
            Dictionary with update result
        """
        from .serializers import UserUpdateSerializer
        
        serializer = UserUpdateSerializer(user, data=user_data, partial=True)
        if not serializer.is_valid():
            raise ValidationError(f"User update validation failed: {serializer.errors}")
        
        updated_user = serializer.save()
        
        return {
            'user': updated_user,
            'success': True,
            'message': 'User information updated successfully'
        }
