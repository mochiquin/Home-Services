"""
Projects API Views

This module provides comprehensive CRUD operations for managing software projects 
and their members in the Secuflow system.

API Endpoints:
- GET    /api/projects/projects/           - List all projects
- POST   /api/projects/projects/           - Create new project
- GET    /api/projects/projects/{id}/      - Get project details
- PUT    /api/projects/projects/{id}/      - Update project
- DELETE /api/projects/projects/{id}/      - Delete project
- GET    /api/projects/projects/{id}/members/ - Get project members
- POST   /api/projects/projects/{id}/add_member/ - Add member
- DELETE /api/projects/projects/{id}/members/{member_id}/ - Remove member
- PATCH  /api/projects/projects/{id}/members/{member_id}/ - Update member role
- GET    /api/projects/projects/my_projects/ - Get owned projects
- GET    /api/projects/projects/joined_projects/ - Get joined projects
- GET    /api/projects/projects/stats/     - Get project statistics

Authentication: All endpoints require JWT authentication
Permissions: 
- List/Create: Any authenticated user
- View Details: Project owner or member
- Update/Delete: Project owner only
- Member Management: Project owner only

Role Hierarchy:
1. owner: Full control over the project
2. maintainer: Can manage project settings and members
3. reviewer: Can review code and manage issues
4. member: Basic access to project resources
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .models import Project, ProjectMember
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectListSerializer, ProjectMemberSerializer,
    ProjectMemberCreateSerializer, ProjectStatsSerializer
)
from .services import ProjectService
from accounts.models import UserProfile


class ProjectPagination(PageNumberPagination):
    """Custom pagination for project list."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing projects.
    
    Provides CRUD operations for projects with proper permissions.
    Only project owners and members can access project details.
    """
    
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    pagination_class = ProjectPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ProjectListSerializer
        elif self.action == 'create':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def get_queryset(self):
        """Filter projects based on user permissions using service layer."""
        user = self.request.user
        user_profile = getattr(user, 'profile', None)
        
        if not user_profile:
            return Project.objects.none()
        
        # Use service layer to get user's projects
        return ProjectService.get_user_projects(user_profile)
    
    def create(self, request, *args, **kwargs):
        """Create a new project using service layer."""
        try:
            user_profile = request.user.profile
            
            # Use service layer to create project
            result = ProjectService.create_project(request.data, user_profile)
            
            serializer = self.get_serializer(result['project'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({
                'error': 'Project creation failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Project creation failed',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['list', 'create']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve project details using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to check access
            if not ProjectService.check_project_access(project, user_profile):
                return Response(
                    {'error': 'You do not have permission to view this project.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(project)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve project',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Update project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to update project
            result = ProjectService.update_project(project, request.data, user_profile)
            
            serializer = self.get_serializer(result['project'])
            return Response(serializer.data)
            
        except ValidationError as e:
            return Response({
                'error': 'Project update failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Project update failed',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """Delete project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to delete project
            result = ProjectService.delete_project(project, user_profile)
            
            return Response({
                'message': result['message']
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'error': 'Project deletion failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Project deletion failed',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of a project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to get project members
            result = ProjectService.get_project_members(project, user_profile)
            
            serializer = ProjectMemberSerializer(result['members'], many=True)
            return Response(serializer.data)
            
        except ValidationError as e:
            return Response({
                'error': 'Failed to get project members',
                'details': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'error': 'Failed to get project members',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a new member to the project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            username = request.data.get('username')
            role = request.data.get('role', ProjectMember.Role.MEMBER)
            
            if not username:
                return Response({
                    'error': 'Username is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer to add member
            result = ProjectService.add_project_member(project, username, role, user_profile)
            
            serializer = ProjectMemberSerializer(result['member'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({
                'error': 'Failed to add member',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to add member',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], url_path='members/(?P<member_id>[^/.]+)')
    def remove_member(self, request, pk=None, member_id=None):
        """Remove a member from the project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to remove member
            result = ProjectService.remove_project_member(project, member_id, user_profile)
            
            return Response({
                'message': result['message']
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'error': 'Failed to remove member',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to remove member',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'], url_path='members/(?P<member_id>[^/.]+)')
    def update_member_role(self, request, pk=None, member_id=None):
        """Update a member's role in the project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            new_role = request.data.get('role')
            if not new_role:
                return Response({
                    'error': 'Role is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer to update member role
            result = ProjectService.update_member_role(project, member_id, new_role, user_profile)
            
            serializer = ProjectMemberSerializer(result['member'])
            return Response(serializer.data)
            
        except ValidationError as e:
            return Response({
                'error': 'Failed to update member role',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to update member role',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def my_projects(self, request):
        """Get projects owned by the current user using service layer."""
        try:
            user_profile = request.user.profile
            
            # Use service layer to get owned projects
            owned_projects = ProjectService.get_owned_projects(user_profile)
            
            page = self.paginate_queryset(owned_projects)
            if page is not None:
                serializer = ProjectListSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = ProjectListSerializer(owned_projects, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': 'Failed to get owned projects',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def joined_projects(self, request):
        """Get projects where the current user is a member using service layer."""
        try:
            user_profile = request.user.profile
            
            # Use service layer to get joined projects
            joined_projects = ProjectService.get_joined_projects(user_profile)
            
            page = self.paginate_queryset(joined_projects)
            if page is not None:
                serializer = ProjectListSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = ProjectListSerializer(joined_projects, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': 'Failed to get joined projects',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get project statistics for the current user using service layer."""
        try:
            user_profile = request.user.profile
            
            # Use service layer to get project statistics
            result = ProjectService.get_project_stats(user_profile)
            
            serializer = ProjectStatsSerializer(result)
            return Response(serializer.data)
            
        except ValidationError as e:
            return Response({
                'error': 'Failed to get project statistics',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to get project statistics',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'])
    def update_branch(self, request, pk=None):
        """Update project's default branch using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            new_branch = request.data.get('branch')
            if not new_branch:
                return Response({
                    'error': 'Branch name is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer to update branch
            result = ProjectService.update_project_branch(project, new_branch, user_profile)
            
            serializer = self.get_serializer(result['project'])
            return Response({
                'project': serializer.data,
                'message': result['message']
            })
            
        except ValidationError as e:
            error_message = str(e)
            if "permission" in error_message.lower() or "owner" in error_message.lower() or "maintainer" in error_message.lower():
                return Response({
                    'error': 'Permission denied',
                    'details': str(e)
                }, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({
                    'error': 'Failed to update branch',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to update branch',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """Get all branches for a project's repository using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Check if user has access to the project
            if not ProjectService.check_project_access(project, user_profile):
                return Response({
                    'error': 'You do not have permission to view this project'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Use service layer to get branches
            result = ProjectService.get_project_branches(project)
            
            return Response({
                'branches': result['branches'],
                'current_branch': result['current_branch'],
                'repository_path': result['repository_path']
            })
            
        except ValidationError as e:
            return Response({
                'error': 'Failed to get branches',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to get branches',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def switch_branch(self, request, pk=None):
        """Switch to a different branch in the project's repository using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Check if user has permission to update project settings
            user_membership = project.members.filter(profile=user_profile).first()
            if not (project.owner_profile == user_profile or 
                    (user_membership and user_membership.role in [ProjectMember.Role.OWNER, ProjectMember.Role.MAINTAINER])):
                return Response({
                    'error': 'Only project owner or maintainer can switch branches'
                }, status=status.HTTP_403_FORBIDDEN)
            
            branch_name = request.data.get('branch')
            if not branch_name:
                return Response({
                    'error': 'Branch name is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer to switch branch
            result = ProjectService.switch_project_branch(project, branch_name)
            
            serializer = self.get_serializer(result['project'])
            return Response({
                'project': serializer.data,
                'message': result['message'],
                'current_branch': result['current_branch']
            })
            
        except ValidationError as e:
            return Response({
                'error': 'Failed to switch branch',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to switch branch',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def validate_repository(self, request):
        """Validate a repository URL and get its branches using service layer."""
        try:
            user_profile = request.user.profile
            repo_url = request.data.get('repo_url')
            
            if not repo_url:
                return Response({
                    'error': 'Repository URL is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer to validate repository
            result = ProjectService.validate_and_clone_repository(repo_url, user_profile)
            
            return Response({
                'valid': True,
                'branches': result['branches'],
                'default_branch': result['default_branch'],
                'repo_url': result['repo_url'],
                'message': result['message']
            })
            
        except ValidationError as e:
            return Response({
                'valid': False,
                'error': 'Repository validation failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'valid': False,
                'error': 'Repository validation failed',
                'details': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing project members.
    
    Provides CRUD operations for project members with proper permissions.
    """
    
    queryset = ProjectMember.objects.all()
    serializer_class = ProjectMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter project members based on user permissions."""
        user_profile = self.request.user.profile
        
        # Return members of projects where user is owner or member
        return ProjectMember.objects.filter(
            Q(project__owner_profile=user_profile) | 
            Q(project__members__profile=user_profile)
        ).distinct().order_by('-joined_at')
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Create a new project member with owner permission check."""
        project_id = request.data.get('project')
        if not project_id:
            return Response(
                {'error': 'Project ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user_profile = request.user.profile
        
        # Only owner can add members
        if project.owner_profile != user_profile:
            return Response(
                {'error': 'Only project owner can add members.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProjectMemberCreateSerializer(data=request.data)
        if serializer.is_valid():
            member = serializer.save()
            response_serializer = ProjectMemberSerializer(member)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Update project member with owner permission check."""
        member = self.get_object()
        user_profile = request.user.profile
        
        # Only owner can update members
        if member.project.owner_profile != user_profile:
            return Response(
                {'error': 'Only project owner can update member details.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevent changing owner role
        if member.role == ProjectMember.Role.OWNER:
            return Response(
                {'error': 'Cannot change project owner role.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete project member with owner permission check."""
        member = self.get_object()
        user_profile = request.user.profile
        
        # Only owner can remove members
        if member.project.owner_profile != user_profile:
            return Response(
                {'error': 'Only project owner can remove members.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevent removing the owner
        if member.role == ProjectMember.Role.OWNER:
            return Response(
                {'error': 'Cannot remove project owner.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
