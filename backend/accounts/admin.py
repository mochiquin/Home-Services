from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    """
    Inline admin interface for UserProfile.
    Allows editing profile information directly from the User admin page.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profiles'
    fields = ['phone', 'bio', 'avatar']
    extra = 0

class UserAdmin(BaseUserAdmin):
    """
    Extended User admin interface that includes UserProfile inline.
    Provides enhanced user management capabilities.
    """
    inlines = (UserProfileInline,)
    
    # Enhanced list display
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'is_active', 'is_staff', 'date_joined', 'get_profile_phone'
    ]
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'profile__phone']
    
    # Add profile information to fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': (),
            'description': 'Profile information is managed below in the User Profile section.'
        }),
    )
    
    def get_profile_phone(self, obj):
        """Display user's phone number in the admin list"""
        try:
            return obj.profile.phone if obj.profile.phone else '-'
        except UserProfile.DoesNotExist:
            return '-'
    get_profile_phone.short_description = 'Phone'
    get_profile_phone.admin_order_field = 'profile__phone'

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model.
    Provides detailed management of user profile information.
    """
    list_display = ['user', 'phone', 'get_user_email', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 
        'user__last_name', 'phone'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',),
            'description': 'Associated user account'
        }),
        ('Contact Information', {
            'fields': ('phone',),
            'description': 'User contact details'
        }),
        ('Profile Details', {
            'fields': ('bio', 'avatar'),
            'description': 'User profile information and avatar'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatic timestamp information'
        })
    )
    
    def get_user_email(self, obj):
        """Display user's email in the admin list"""
        return obj.user.email
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'user__email'

# Customize admin site headers
admin.site.site_header = 'Secuflow User Management System'
admin.site.site_title = 'Secuflow Admin'
admin.site.index_title = 'Welcome to Secuflow User Management Admin'