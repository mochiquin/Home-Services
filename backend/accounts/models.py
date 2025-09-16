from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """Extended profile data for Django's built-in User.

    Stores additional attributes such as avatar and display fields.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name="User"
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name="Contact Email",
        help_text="Preferred contact email (defaults to account email)"
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="First name",
        help_text="User given name stored on profile"
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Last name",
        help_text="User family name stored on profile"
    )
    username = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Profile Username",
        help_text="Auto-generated from first and last name"
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
        return f"UserProfile(user_id={self.user_id})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Default contact_email to the linked user's email if not provided
        if not self.contact_email:
            self.contact_email = self.user.email or ''
        # Auto-generate profile username from first and last name if not set
        if not self.username:
            base_first = (self.first_name or '').strip()
            base_last = (self.last_name or '').strip()
            combined = f"{base_first}{base_last}".strip()
            self.username = combined or self.user.username
        super().save(*args, **kwargs)