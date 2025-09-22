from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """Extended profile data for Django's built-in User.

    Stores additional attributes such as avatar and display name.
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