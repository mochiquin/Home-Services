from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """
    Extended user profile model to store additional user information.
    Linked to Django's built-in User model via OneToOneField.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name="User"
    )
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Phone Number",
        help_text="User's phone number"
    )
    bio = models.TextField(
        max_length=500, 
        blank=True, 
        verbose_name="Biography",
        help_text="Brief description about the user"
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

    def __str__(self):
        return f"{self.user.username} Profile"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']