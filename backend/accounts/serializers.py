from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for basic user information.
    Returns read-only fields for security purposes.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active']
        read_only_fields = ['id', 'date_joined']

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    Includes nested user data for complete profile view.
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['user', 'phone', 'bio', 'avatar', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user serializer that includes profile information.
    Used for complete user information display.
    """
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active', 'profile']
        read_only_fields = ['id', 'date_joined']

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Includes password confirmation and validation.
    """
    password = serializers.CharField(
        write_only=True, 
        min_length=8, 
        style={'input_type': 'password'},
        help_text="Password must be at least 8 characters long"
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        style={'input_type': 'password'},
        help_text="Confirm your password"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate(self, data):
        """Validate that passwords match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def validate_username(self, value):
        """Validate that username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists")
        return value
    
    def validate_email(self, value):
        """Validate that email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email address already exists")
        return value
    
    def create(self, validated_data):
        """Create new user and associated profile"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        # Automatically create user profile
        UserProfile.objects.create(user=user)
        return user

class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change functionality.
    Requires old password verification and new password confirmation.
    """
    old_password = serializers.CharField(
        required=True, 
        style={'input_type': 'password'},
        help_text="Your current password"
    )
    new_password = serializers.CharField(
        required=True, 
        min_length=8, 
        style={'input_type': 'password'},
        help_text="New password must be at least 8 characters long"
    )
    new_password_confirm = serializers.CharField(
        required=True, 
        style={'input_type': 'password'},
        help_text="Confirm your new password"
    )
    
    def validate(self, data):
        """Validate that new passwords match"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("New passwords do not match")
        return data
    
    def validate_old_password(self, value):
        """Validate that old password is correct"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user basic information.
    Only allows modification of safe fields.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def validate_email(self, value):
        """Validate that email is unique among other users"""
        user = self.instance
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This email is already in use by another user")
        return value
