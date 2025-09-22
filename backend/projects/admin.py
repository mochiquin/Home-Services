from django.contrib import admin
from .models import Project, ProjectMember


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for Project model."""
    
    list_display = [
        'id', 'name', 'repo_url', 'default_branch', 
        'owner_profile', 'created_at', 'updated_at'
    ]
    list_filter = ['created_at', 'updated_at', 'default_branch']
    search_fields = ['name', 'repo_url', 'owner_profile__user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'repo_url', 'default_branch')
        }),
        ('Ownership', {
            'fields': ('owner_profile',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('owner_profile__user')


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    """Admin configuration for ProjectMember model."""
    
    list_display = [
        'id', 'project', 'profile', 'role', 'joined_at'
    ]
    list_filter = ['role', 'joined_at', 'project']
    search_fields = [
        'project__name', 'profile__user__username', 
        'profile__user__email'
    ]
    readonly_fields = ['id', 'joined_at']
    
    fieldsets = (
        ('Membership', {
            'fields': ('project', 'profile', 'role')
        }),
        ('Timestamps', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'project', 'profile__user'
        )

