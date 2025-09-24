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

import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q
from accounts.models import User
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .models import Project, ProjectMember
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectListSerializer, ProjectMemberSerializer,
    ProjectMemberCreateSerializer, ProjectStatsSerializer
)
from .services import ProjectService
from common.git_utils import GitPermissionError
from accounts.models import UserProfile
from common.response import ApiResponse

# Initialize logger for projects API
logger = logging.getLogger(__name__)


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
    lookup_field = 'id'
    
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
        user_id = request.user.id if request.user else None
        project_name = request.data.get('name', '')
        
        logger.info("Creating new project", extra={
            'user_id': user_id,
            'project_name': project_name
        })
        
        try:
            user_profile = request.user.profile
            
            # Use service layer to create project
            result = ProjectService.create_project(request.data, user_profile)
            
            logger.info("Project created successfully", extra={
                'user_id': user_id,
                'project_name': project_name,
                'project_id': result['project'].id
            })
            
            serializer = self.get_serializer(result['project'])
            return ApiResponse.created(
                data=serializer.data,
                message=result.get('message', 'Project created successfully')
            )
            
        except GitPermissionError as e:
            logger.warning("Project creation failed - Git permission error", extra={
                'user_id': user_id,
                'project_name': project_name,
                'error_type': e.error_type,
                'error': str(e)
            })
            return ApiResponse.error(
                error_message=e.message,
                error_code=f"GIT_{e.error_type}",
                status_code=status.HTTP_403_FORBIDDEN,
                data={
                    'error_type': e.error_type,
                    'solution': e.solution,
                    'stderr': e.stderr
                }
            )
        except ValidationError as e:
            logger.warning("Project creation failed - validation error", extra={
                'user_id': user_id,
                'project_name': project_name,
                'error': str(e)
            })
            return ApiResponse.error(
                error_message=str(e),
                error_code="PROJECT_CREATION_ERROR"
            )
        except Exception as e:
            logger.error("Project creation failed - system error", extra={
                'user_id': user_id,
                'project_name': project_name,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Project creation failed",
                error_code="PROJECT_CREATION_ERROR"
            )
    
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
                return ApiResponse.forbidden(
                    error_message="You do not have permission to view this project",
                    error_code="ACCESS_DENIED"
                )
            
            serializer = self.get_serializer(project)
            return ApiResponse.success(
                data=serializer.data,
                message="Project retrieved successfully"
            )
            
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Failed to retrieve project",
                error_code="PROJECT_RETRIEVAL_ERROR"
            )
    
    def update(self, request, *args, **kwargs):
        """Update project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to update project
            result = ProjectService.update_project(project, request.data, user_profile)
            
            serializer = self.get_serializer(result['project'])
            return ApiResponse.success(
                data=serializer.data,
                message=result.get('message', 'Project updated successfully')
            )
            
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="PROJECT_UPDATE_ERROR"
            )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Project update failed",
                error_code="PROJECT_UPDATE_ERROR"
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to delete project
            result = ProjectService.delete_project(project, user_profile)
            
            return ApiResponse.success(
                message=result['message']
            )
            
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="PROJECT_DELETION_ERROR"
            )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Project deletion failed",
                error_code="PROJECT_DELETION_ERROR"
            )
    
    @action(detail=True, methods=['get'])
    def members(self, request, id=None):
        """Get all members of a project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Use service layer to get project members
            result = ProjectService.get_project_members(project, user_profile)
            
            serializer = ProjectMemberSerializer(result['members'], many=True)
            return ApiResponse.success(
                data=serializer.data,
                message=result.get('message', 'Project members retrieved successfully')
            )
            
        except ValidationError as e:
            return ApiResponse.forbidden(
                error_message=str(e),
                error_code="ACCESS_DENIED"
            )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Failed to get project members",
                error_code="MEMBERS_RETRIEVAL_ERROR"
            )
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, id=None):
        """Add a new member to the project using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            user_id = request.data.get('user_id')
            role_id = request.data.get('role_id', 3)  # Default to reviewer (ID: 3)
            
            if not user_id:
                return ApiResponse.error(
                    error_message="user_id is required",
                    error_code="MISSING_USER_ID"
                )
            
            if not role_id:
                return ApiResponse.error(
                    error_message="role_id is required",
                    error_code="MISSING_ROLE_ID"
                )
            
            # Use service layer to add member
            result = ProjectService.add_project_member_by_user_id(project, user_id, role_id, user_profile)
            
            serializer = ProjectMemberSerializer(result['member'])
            return ApiResponse.created(
                data=serializer.data,
                message=result.get('message', 'Member added successfully')
            )
            
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="MEMBER_ADDITION_ERROR"
            )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Failed to add member",
                error_code="MEMBER_ADDITION_ERROR"
            )
    
    
    
    @action(detail=True, methods=['delete'], url_path='members/by-user/(?P<user_id>[^/.]+)')
    def remove_member_by_user(self, request, id=None, user_id=None):
        """Remove a member by user UUID using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            result = ProjectService.remove_project_member_by_user_id(project, user_id, user_profile)
            return ApiResponse.success(
                message=result['message']
            )
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="MEMBER_REMOVAL_ERROR"
            )
        except Exception:
            return ApiResponse.internal_error(
                error_message="Failed to remove member",
                error_code="MEMBER_REMOVAL_ERROR"
            )

    

    @action(detail=True, methods=['patch'], url_path='members/by-user/(?P<user_id>[^/.]+)')
    def update_member_role_by_user(self, request, id=None, user_id=None):
        """Update a member's role by user UUID using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            new_role = request.data.get('role')
            if not new_role:
                return ApiResponse.error(
                    error_message="Role is required",
                    error_code="MISSING_ROLE"
                )
            result = ProjectService.update_member_role_by_user_id(project, user_id, new_role, user_profile)
            serializer = ProjectMemberSerializer(result['member'])
            return ApiResponse.success(
                data=serializer.data,
                message=result.get('message', 'Member role updated successfully')
            )
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="MEMBER_ROLE_UPDATE_ERROR"
            )
        except Exception:
            return ApiResponse.internal_error(
                error_message="Failed to update member role",
                error_code="MEMBER_ROLE_UPDATE_ERROR"
            )
    
    @action(detail=False, methods=['get'])
    def my_projects(self, request):
        """Get projects owned by the current user using service layer."""
        user_id = request.user.id if request.user else None
        
        logger.info("User owned projects request", extra={
            'user_id': user_id
        })
        
        try:
            user_profile = request.user.profile
            
            # Use service layer to get owned projects
            owned_projects = ProjectService.get_owned_projects(user_profile)
            
            logger.debug("User owned projects retrieved successfully", extra={
                'user_id': user_id,
                'projects_count': owned_projects.count()
            })
            
            page = self.paginate_queryset(owned_projects)
            if page is not None:
                serializer = ProjectListSerializer(page, many=True)
                # Build paginated response manually using ApiResponse to avoid rendering issues
                paginator = self.paginator
                return ApiResponse.success(data={
                    'results': serializer.data,
                    'count': paginator.page.paginator.count,
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link()
                })
            
            serializer = ProjectListSerializer(owned_projects, many=True)
            return ApiResponse.success(data=serializer.data)
            
        except Exception as e:
            logger.error("Failed to retrieve user owned projects", extra={
                'user_id': user_id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to get owned projects",
                error_code="MY_PROJECTS_ERROR"
            )
    
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
                # Build paginated response manually using ApiResponse to avoid rendering issues
                paginator = self.paginator
                return ApiResponse.success(data={
                    'results': serializer.data,
                    'count': paginator.page.paginator.count,
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link()
                })
            
            serializer = ProjectListSerializer(joined_projects, many=True)
            return ApiResponse.success(data=serializer.data)
            
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Failed to get joined projects",
                error_code="JOINED_PROJECTS_ERROR"
            )
    
    @action(detail=False, methods=['get'])
    def selectable_projects(self, request):
        """Get projects that user can select for TNM analysis (owned or maintainer role)."""
        try:
            user_profile = request.user.profile
            
            # Get projects where user is owner or maintainer (can run TNM)
            user_projects = Project.objects.filter(
                Q(owner_profile=user_profile) | 
                Q(members__profile=user_profile, members__role__in=[ProjectMember.Role.OWNER, ProjectMember.Role.MAINTAINER])
            ).distinct().order_by('-created_at')
            
            # Filter projects that have repositories
            projects_with_repos = user_projects.filter(repo_url__isnull=False).exclude(repo_url='')
            
            page = self.paginate_queryset(projects_with_repos)
            if page is not None:
                serializer = ProjectListSerializer(page, many=True)
                # Build paginated response manually using ApiResponse to avoid rendering issues
                paginator = self.paginator
                return ApiResponse.success(data={
                    'results': serializer.data,
                    'count': paginator.page.paginator.count,
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link()
                })
            
            serializer = ProjectListSerializer(projects_with_repos, many=True)
            return ApiResponse.success(
                data={
                    'projects': serializer.data,
                    'count': projects_with_repos.count()
                },
                message='Projects available for TNM analysis'
            )
            
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Failed to get selectable projects",
                error_code="SELECTABLE_PROJECTS_ERROR"
            )

    @action(detail=False, methods=['post'])
    def select_project(self, request):
        """Persist user's selected project for quick TNM operations.
        Body: { "project_uid": "<uuid>" }
        """
        try:
            user_profile = request.user.profile
            project_uid = request.data.get('project_uid')
            if not project_uid:
                return ApiResponse.error('project_uid is required', error_code='MISSING_PROJECT_UID', status_code=status.HTTP_400_BAD_REQUEST)
            project = Project.objects.filter(id=project_uid).first()
            if not project:
                return ApiResponse.not_found('Project not found')
            # Only owner or maintainer can select for TNM
            membership = project.members.filter(profile=user_profile).first()
            if not (project.owner_profile == user_profile or (membership and membership.role in [ProjectMember.Role.OWNER, ProjectMember.Role.MAINTAINER])):
                return ApiResponse.forbidden('Only project owner or maintainer can select this project')
            user_profile.selected_project = project
            user_profile.save(update_fields=['selected_project'])
            return ApiResponse.success(data={'project_uid': str(project.id), 'project_name': project.name}, message='Selected project updated')
        except Exception:
            return ApiResponse.internal_error('Failed to select project', error_code='SELECT_PROJECT_ERROR')
    
    @action(detail=False, methods=['get'])
    def roles(self, request):
        """Get all available project roles."""
        try:
            from .models import ProjectRole
            roles = ProjectRole.get_all_roles()
            return ApiResponse.success(
                data=roles,
                message="Project roles retrieved successfully"
            )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Failed to get project roles",
                error_code="ROLES_RETRIEVAL_ERROR"
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get project statistics for the current user using service layer."""
        try:
            user_profile = request.user.profile
            
            # Use service layer to get project statistics
            result = ProjectService.get_project_stats(user_profile)
            
            serializer = ProjectStatsSerializer(result)
            return ApiResponse.success(data=serializer.data)
            
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="PROJECT_STATS_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message="Failed to get project statistics",
                error_code="PROJECT_STATS_ERROR"
            )
    
    @action(detail=True, methods=['patch'])
    def update_branch(self, request, id=None):
        """Update project's default branch using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            new_branch = request.data.get('branch')
            if not new_branch:
                return ApiResponse.error('Branch name is required', error_code='MISSING_BRANCH', status_code=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer to update branch
            result = ProjectService.update_project_branch(project, new_branch, user_profile)
            
            serializer = self.get_serializer(result['project'])
            return ApiResponse.success(data={'project': serializer.data}, message=result['message'])
            
        except ValidationError as e:
            error_message = str(e)
            if "permission" in error_message.lower() or "owner" in error_message.lower() or "maintainer" in error_message.lower():
                return ApiResponse.forbidden(error_message='Permission denied', error_code='PERMISSION_DENIED')
            else:
                return ApiResponse.error(
                    error_message=str(e),
                    error_code='UPDATE_BRANCH_ERROR',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message=str(e),
                error_code='UPDATE_BRANCH_ERROR'
            )
    
    @action(detail=True, methods=['get'])
    def branches(self, request, id=None):
        """Get all branches for a project's repository using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Check if user has access to the project
            if not ProjectService.check_project_access(project, user_profile):
                return ApiResponse.forbidden(
                    error_message="You do not have permission to view this project",
                    error_code="ACCESS_DENIED"
                )
            
            # Use service layer to get branches
            result = ProjectService.get_project_branches(project)
            
            return ApiResponse.success(
                data={
                    'branches': result['branches'],
                    'current_branch': result['current_branch'],
                    'repository_path': result['repository_path']
                },
                message="Project branches retrieved successfully"
            )
            
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="BRANCHES_RETRIEVAL_ERROR"
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in branches: {str(e)}")
            print(f"Traceback: {error_details}")
            return ApiResponse.internal_error(
                error_message="Failed to get branches",
                error_code="BRANCHES_RETRIEVAL_ERROR"
            )
    
    @action(detail=True, methods=['post'])
    def switch_branch(self, request, id=None):
        """Switch to a different branch in the project's repository using service layer."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Check if user has permission to update project settings
            user_membership = project.members.filter(profile=user_profile).first()
            if not (project.owner_profile == user_profile or 
                    (user_membership and user_membership.role in [ProjectMember.Role.OWNER, ProjectMember.Role.MAINTAINER])):
                return ApiResponse.forbidden(
                    error_message="Only project owner or maintainer can switch branches",
                    error_code="ACCESS_DENIED"
                )
            
            branch_id = request.data.get('branch_id')
            
            if not branch_id:
                return ApiResponse.error(
                    error_message="branch_id is required",
                    error_code="MISSING_BRANCH_ID"
                )
            
            # Get all branches to find the one with matching branch_id
            branches_result = ProjectService.get_project_branches(project)
            target_branch = None
            for branch in branches_result['branches']:
                if branch['branch_id'] == branch_id:
                    target_branch = branch
                    break
            
            if not target_branch:
                return ApiResponse.error(
                    error_message=f"Branch with ID {branch_id} not found",
                    error_code="BRANCH_NOT_FOUND"
                )
            
            branch_name = target_branch['name']
            
            # Use service layer to switch branch
            result = ProjectService.switch_project_branch(project, branch_name)
            
            serializer = self.get_serializer(result['project'])
            return ApiResponse.success(
                data={
                    'project': serializer.data,
                    'current_branch': result['current_branch']
                },
                message=result['message']
            )
            
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="BRANCH_SWITCH_ERROR"
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in switch_branch: {str(e)}")
            print(f"Traceback: {error_details}")
            return ApiResponse.internal_error(
                error_message="Failed to switch branch",
                error_code="BRANCH_SWITCH_ERROR"
            )
    
    @action(detail=False, methods=['post'])
    def validate_repository(self, request):
        """Validate a repository URL and get its branches using service layer."""
        try:
            user_profile = request.user.profile
            repo_url = request.data.get('repo_url')
            
            if not repo_url:
                return ApiResponse.error('Repository URL is required', error_code='MISSING_REPO_URL', status_code=status.HTTP_400_BAD_REQUEST)
            
            # Use service layer to validate repository
            result = ProjectService.validate_and_clone_repository(repo_url, user_profile)
            
            return ApiResponse.success(
                data={
                    'valid': True,
                    'branches': result['branches'],
                    'default_branch': result['default_branch'],
                    'repo_url': result['repo_url']
                },
                message=result['message']
            )
            
        except GitPermissionError as e:
            return ApiResponse.error(
                error_message=e.message,
                error_code=f'GIT_{e.error_type}',
                status_code=status.HTTP_403_FORBIDDEN,
                data={
                    'valid': False,
                    'error_type': e.error_type,
                    'solution': e.solution,
                    'stderr': e.stderr
                }
            )
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code='REPO_VALIDATION_ERROR',
                status_code=status.HTTP_400_BAD_REQUEST,
                data={'valid': False}
            )
        except Exception as e:
            return ApiResponse.internal_error(
                error_message='Repository validation failed',
                error_code='REPO_VALIDATION_ERROR'
            )
    
    @action(detail=True, methods=['post'])
    def retry_repository_access(self, request, id=None):
        """Retry repository access after fixing authentication issues."""
        try:
            project = self.get_object()
            user_profile = request.user.profile
            
            # Check if user has permission to update project
            if not ProjectService.check_project_access(project, user_profile):
                return ApiResponse.forbidden(
                    error_message="You do not have permission to access this project",
                    error_code="ACCESS_DENIED"
                )
            
            if not project.repo_url:
                return ApiResponse.error(
                    error_message="Project has no repository URL configured",
                    error_code="NO_REPOSITORY_URL"
                )
            
            logger.info("Retrying repository access", extra={
                'user_id': request.user.id,
                'project_id': project.id,
                'repo_url': project.repo_url
            })
            
            # Try to validate repository access again
            try:
                validation_result = ProjectService.validate_and_clone_repository(project.repo_url, user_profile)
                
                # Try to clone/update the repository if validation succeeds
                try:
                    clone_result = ProjectService.clone_repository_for_project(project, project.repo_url)
                    
                    logger.info("Repository retry successful - cloned", extra={
                        'user_id': request.user.id,
                        'project_id': project.id,
                        'used_authentication': clone_result.get('used_authentication', False)
                    })
                    
                    return ApiResponse.success(
                        data={
                            'status': 'success',
                            'action': 'cloned',
                            'repository_info': {
                                'branches': clone_result.get('branches', []),
                                'current_branch': clone_result.get('current_branch'),
                                'used_authentication': clone_result.get('used_authentication', False)
                            }
                        },
                        message="Repository access restored and repository cloned successfully"
                    )
                    
                except Exception as clone_error:
                    # If cloning fails but validation succeeded, still report partial success
                    logger.warning("Repository retry partially successful - validation only", extra={
                        'user_id': request.user.id,
                        'project_id': project.id,
                        'clone_error': str(clone_error)
                    })
                    
                    return ApiResponse.success(
                        data={
                            'status': 'partial_success',
                            'action': 'validated',
                            'validation_info': {
                                'branches': validation_result.get('branches', []),
                                'default_branch': validation_result.get('default_branch'),
                                'used_authentication': validation_result.get('used_authentication', False)
                            },
                            'warning': f"Repository is accessible but cloning failed: {str(clone_error)}"
                        },
                        message="Repository access restored but cloning failed"
                    )
                    
            except GitPermissionError as e:
                logger.warning("Repository retry failed - still permission issues", extra={
                    'user_id': request.user.id,
                    'project_id': project.id,
                    'error_type': e.error_type,
                    'error': str(e)
                })
                
                return ApiResponse.error(
                    error_message=f"Repository access still failed: {e.message}",
                    error_code=f"GIT_{e.error_type}",
                    status_code=status.HTTP_403_FORBIDDEN,
                    data={
                        'status': 'failed',
                        'error_type': e.error_type,
                        'solution': e.solution,
                        'stderr': e.stderr
                    }
                )
                
        except Exception as e:
            logger.error("Repository retry failed - system error", extra={
                'user_id': request.user.id,
                'project_id': project.id if 'project' in locals() else None,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retry repository access",
                error_code="REPOSITORY_RETRY_ERROR"
            )


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
