from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import RegexValidator
from cryptography.fernet import Fernet
import uuid
import base64


class User(AbstractUser):
    """Custom user model with UUID primary key and password strength requirements."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Password strength configuration
    password_min_length = models.IntegerField(default=8, help_text="Minimum password length")
    require_uppercase = models.BooleanField(default=True, help_text="Require uppercase letter")
    require_lowercase = models.BooleanField(default=True, help_text="Require lowercase letter") 
    require_numbers = models.BooleanField(default=True, help_text="Require numbers")

    class Meta:
        db_table = 'auth_user'


class UserProfile(models.Model):
    """Extended profile data for Django's built-in User.

    Stores additional attributes such as avatar and display name.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'accounts.User', 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name="User"
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name="Contact Email",
        help_text="Preferred contact email (defaults to account email)"
    )
    display_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Display Name",
        help_text="Public display name (defaults to username)"
    )
    avatar = models.ImageField(
        upload_to='avatars/', 
        blank=True, 
        null=True, 
        verbose_name="Avatar",
        help_text="User's profile picture"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Updated At"
    )
    last_activity = models.DateTimeField(null=True, blank=True, help_text="Last user activity timestamp")

    def __str__(self):
        return f"UserProfile(user_id={self.user_id}, display_name={self.display_name})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Default contact_email to the linked user's email if not provided
        if not self.contact_email:
            self.contact_email = self.user.email or ''
        # Auto-generate display_name from first_name + last_name, fallback to email
        first_name = (self.user.first_name or '').strip()
        last_name = (self.user.last_name or '').strip()
        if first_name or last_name:
            self.display_name = f"{first_name} {last_name}".strip()
        else:
            self.display_name = self.user.email or self.user.username
        super().save(*args, **kwargs)


class GitCredential(models.Model):
    """Store encrypted Git authentication credentials for users."""
    
    class CredentialType(models.TextChoices):
        HTTPS_TOKEN = "https_token", "HTTPS Personal Access Token"
        SSH_KEY = "ssh_key", "SSH Private Key"
        BASIC_AUTH = "basic_auth", "Username/Password"
    
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='git_credentials'
    )
    
    credential_type = models.CharField(
        max_length=20,
        choices=CredentialType.choices,
        default=CredentialType.HTTPS_TOKEN
    )
    
    provider = models.CharField(
        max_length=50,
        default='github',
        help_text="Git provider (github, gitlab, bitbucket, etc.)"
    )
    
    # Encrypted credential data
    encrypted_data = models.TextField(
        help_text="Encrypted credential data (token, username/password, ssh key)"
    )
    
    username = models.CharField(
        max_length=255,
        blank=True,
        help_text="Username for basic auth or git user"
    )
    
    is_active = models.BooleanField(default=True)
    
    # Enhanced fields for better credential management
    description = models.CharField(max_length=200, blank=True, help_text="User-defined description for this credential")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Credential expiration time")
    last_used_at = models.DateTimeField(null=True, blank=True, help_text="Last time this credential was used")
    scopes = models.JSONField(default=list, blank=True, help_text="Token permission scopes")
    use_count = models.IntegerField(default=0, help_text="Number of times this credential has been used")
    last_error = models.TextField(blank=True, help_text="Last error message when using this credential")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user_profile', 'provider', 'credential_type']
        verbose_name = "Git Credential"
        verbose_name_plural = "Git Credentials"
    
    def __str__(self):
        return f"GitCredential({self.user_profile.user.username}, {self.provider}, {self.credential_type})"
    
    @classmethod
    def _get_encryption_key(cls):
        """Get encryption key from settings or generate one."""
        key = getattr(settings, 'GIT_CREDENTIAL_ENCRYPTION_KEY', None)
        if not key:
            # Generate a key for development - in production this should be set in settings
            key = Fernet.generate_key()
        if isinstance(key, str):
            key = key.encode()
        return key
    
    def encrypt_credential(self, credential_data):
        """Encrypt credential data before storing."""
        try:
            f = Fernet(self._get_encryption_key())
            if isinstance(credential_data, str):
                credential_data = credential_data.encode()
            encrypted = f.encrypt(credential_data)
            self.encrypted_data = base64.b64encode(encrypted).decode()
        except Exception as e:
            raise ValueError(f"Failed to encrypt credential: {str(e)}")
    
    def decrypt_credential(self):
        """Decrypt and return credential data."""
        try:
            f = Fernet(self._get_encryption_key())
            encrypted_bytes = base64.b64decode(self.encrypted_data.encode())
            decrypted = f.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt credential: {str(e)}")
    
    def set_token(self, token):
        """Set a personal access token."""
        self.credential_type = self.CredentialType.HTTPS_TOKEN
        self.encrypt_credential(token)
    
    def set_basic_auth(self, username, password):
        """Set username/password for basic auth."""
        self.credential_type = self.CredentialType.BASIC_AUTH
        self.username = username
        self.encrypt_credential(password)
    
    def set_ssh_key(self, private_key, username='git'):
        """Set SSH private key."""
        self.credential_type = self.CredentialType.SSH_KEY
        self.username = username
        self.encrypt_credential(private_key)
    
    def is_expired(self):
        """Check if credential is expired."""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def mark_used(self, error_message=None):
        """Mark credential as used and optionally record error."""
        from django.utils import timezone
        self.last_used_at = timezone.now()
        self.use_count += 1
        if error_message:
            self.last_error = error_message
        else:
            self.last_error = ""
        self.save(update_fields=['last_used_at', 'use_count', 'last_error'])
    
    def get_display_name(self):
        """Get user-friendly display name for this credential."""
        if self.description:
            return self.description
        return f"{self.provider} {self.get_credential_type_display()}"

    def get_auth_url(self, repo_url):
        """Get authenticated URL for repository access."""
        if self.credential_type == self.CredentialType.HTTPS_TOKEN:
            token = self.decrypt_credential()
            # For GitHub, GitLab, etc., use token in URL
            if repo_url.startswith('https://github.com/'):
                return repo_url.replace('https://github.com/', f'https://{token}@github.com/')
            elif repo_url.startswith('https://gitlab.com/'):
                return repo_url.replace('https://gitlab.com/', f'https://oauth2:{token}@gitlab.com/')
            else:
                # Generic HTTPS with token
                return repo_url.replace('https://', f'https://{token}@')
        elif self.credential_type == self.CredentialType.BASIC_AUTH:
            password = self.decrypt_credential()
            if repo_url.startswith('https://'):
                return repo_url.replace('https://', f'https://{self.username}:{password}@')
        
        return repo_url  # Return original URL if no auth can be applied