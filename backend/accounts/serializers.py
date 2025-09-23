from rest_framework import serializers
from .models import User, UserProfile

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
        fields = ['user', 'contact_email', 'display_name', 'avatar', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class UserProfileUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating user profile information.
    Only allows updating contact_email, first_name, and last_name.
    display_name is auto-generated from first_name + last_name.
    Uses service layer for business logic.
    """
    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text="User's first name"
    )
    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text="User's last name"
    )
    contact_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Contact email address"
    )
    
    def validate_contact_email(self, value):
        """Validate contact email if provided"""
        if value and len(value.strip()) == 0:
            return None
        return value
    
    def validate_first_name(self, value):
        """Validate first name if provided"""
        if value and len(value.strip()) == 0:
            return None
        return value
    
    def validate_last_name(self, value):
        """Validate last name if provided"""
        if value and len(value.strip()) == 0:
            return None
        return value
    
    def update(self, instance, validated_data):
        """
        Update user profile using service layer.
        This method is called by DRF but we delegate to service layer.
        """
        # Import here to avoid circular imports
        from .services import UserProfileService
        
        # Use service layer for business logic
        result = UserProfileService.update_user_profile(instance.user, validated_data)
        
        # Return the updated profile instance
        return result['profile']

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
    Only requires email, password, and password confirmation.
    Username is automatically generated from email.
    Display name defaults to email, can be updated later via profile update.
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
        fields = ['email', 'password', 'password_confirm']
    
    def validate(self, data):
        """Validate that passwords match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def validate_email(self, value):
        """Validate that email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email address already exists")
        return value
    
    def create(self, validated_data):
        """Create new user and associated profile"""
        validated_data.pop('password_confirm')
        email = validated_data.get('email')
        password = validated_data.get('password')
        
        # Auto-generate a unique username from email local part
        base_username = (email.split('@')[0] if email else 'user').strip() or 'user'
        candidate = base_username
        counter = 1
        while User.objects.filter(username=candidate).exists():
            counter += 1
            candidate = f"{base_username}{counter}"
        
        # Create user with auto-generated username (no first_name, last_name)
        user = User.objects.create_user(
            username=candidate, 
            email=email, 
            password=password
        )
        
        # Automatically create user profile
        # display_name will be auto-generated in UserProfile.save() method (defaults to email)
        UserProfile.objects.create(
            user=user, 
            contact_email=user.email
        )
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
