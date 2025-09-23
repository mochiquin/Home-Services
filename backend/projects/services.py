"""
Project service layer for handling all project-related business logic.
Separates business logic from views and serializers.
"""
import os
from django.db import transaction
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from accounts.models import User
from django.conf import settings
from .models import Project, ProjectMember
from accounts.models import UserProfile
from common.git_utils import GitUtils
import threading
import os


class ProjectService:
    """Service class for all project-related operations."""
    
    @staticmethod
    def get_user_projects(user_profile):
        """
        Get projects where user is owner or member.
        
        Args:
            user_profile: UserProfile instance
            
        Returns:
            QuerySet of projects
        """
        return Project.objects.filter(
            Q(owner_profile=user_profile) | 
            Q(members__profile=user_profile)
        ).distinct().order_by('-created_at')
    
    @staticmethod
    def get_owned_projects(user_profile):
        """
        Get projects owned by user.
        
        Args:
            user_profile: UserProfile instance
            
        Returns:
            QuerySet of owned projects
        """
        return Project.objects.filter(owner_profile=user_profile).order_by('-created_at')
    
    @staticmethod
    def get_joined_projects(user_profile):
        """
        Get projects where user is a member (but not owner).
        
        Args:
            user_profile: UserProfile instance
            
        Returns:
            QuerySet of joined projects
        """
        return Project.objects.filter(
            members__profile=user_profile
        ).exclude(owner_profile=user_profile).distinct().order_by('-created_at')
    
    @staticmethod
    def check_project_access(project, user_profile):
        """
        Check if user has access to project.
        
        Args:
            project: Project instance
            user_profile: UserProfile instance
            
        Returns:
            Boolean indicating access
        """
        return (project.owner_profile == user_profile or 
                project.members.filter(profile=user_profile).exists())
    
    @staticmethod
    def check_owner_permission(project, user_profile):
        """
        Check if user is project owner.
        
        Args:
            project: Project instance
            user_profile: UserProfile instance
            
        Returns:
            Boolean indicating ownership
        """
        return project.owner_profile == user_profile
    
    @staticmethod
    @transaction.atomic
    def create_project(project_data, owner_profile):
        """
        Create a new project with owner as member.
        If repo_url is provided, clone the repository.
        
        Args:
            project_data: Dictionary containing project data
            owner_profile: UserProfile instance of the owner
            
        Returns:
            Dictionary with creation result
        """
        try:
            # Create project
            project = Project.objects.create(
                name=project_data['name'],
                repo_url=project_data['repo_url'],
                default_branch=project_data.get('default_branch', ''),
                owner_profile=owner_profile
            )
            
            # Automatically add owner as project member
            ProjectMember.objects.create(
                project=project,
                profile=owner_profile,
                role=ProjectMember.Role.OWNER
            )
            
            # If repository URL is provided, clone the repository
            repo_url = project_data.get('repo_url')
            if repo_url:
                try:
                    clone_result = ProjectService.clone_repository_for_project(project, repo_url)
                    return {
                        'project': project,
                        'success': True,
                        'message': 'Project created and repository cloned successfully',
                        'repository_info': {
                            'branches': clone_result['branches'],
                            'current_branch': clone_result['current_branch'],
                            'repository_path': clone_result['repository_path']
                        }
                    }
                except ValidationError as e:
                    # If cloning fails, still return the project but with a warning
                    return {
                        'project': project,
                        'success': True,
                        'message': 'Project created successfully, but repository cloning failed',
                        'warning': str(e)
                    }
            
            return {
                'project': project,
                'success': True,
                'message': 'Project created successfully'
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to create project: {str(e)}")
    
    @staticmethod
    def update_project(project, project_data, user_profile):
        """
        Update project details.
        
        Args:
            project: Project instance
            project_data: Dictionary containing update data
            user_profile: UserProfile instance
            
        Returns:
            Dictionary with update result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can update project details")
        
        try:
            # Update project fields
            for field, value in project_data.items():
                if hasattr(project, field):
                    setattr(project, field, value)
            
            project.save()
            
            return {
                'project': project,
                'success': True,
                'message': 'Project updated successfully'
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to update project: {str(e)}")
    
    @staticmethod
    def delete_project(project, user_profile):
        """
        Delete project.
        
        Args:
            project: Project instance
            user_profile: UserProfile instance
            
        Returns:
            Dictionary with deletion result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can delete the project")
        
        try:
            project_name = project.name
            project.delete()
            
            return {
                'success': True,
                'message': f'Project "{project_name}" deleted successfully'
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to delete project: {str(e)}")
    
    @staticmethod
    def get_project_members(project, user_profile):
        """
        Get all members of a project.
        
        Args:
            project: Project instance
            user_profile: UserProfile instance
            
        Returns:
            Dictionary with members data
        """
        if not ProjectService.check_project_access(project, user_profile):
            raise ValidationError("You do not have permission to view project members")
        
        members = project.members.all().order_by('joined_at')
        
        return {
            'members': members,
            'count': members.count(),
            'success': True
        }
    
    @staticmethod
    @transaction.atomic
    def add_project_member(project, username, role, user_profile):
        """
        Add a new member to the project.
        
        Args:
            project: Project instance
            username: Username of the user to add
            role: Role to assign to the member
            user_profile: UserProfile instance of the requester
            
        Returns:
            Dictionary with addition result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can add members")
        
        try:
            # Get user by username
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise ValidationError("User with this username does not exist")
            
            target_profile = user.profile
            
            # Check if user is already a member
            if ProjectMember.objects.filter(project=project, profile=target_profile).exists():
                raise ValidationError("This user is already a member of this project")
            
            # Create project member
            member = ProjectMember.objects.create(
                project=project,
                profile=target_profile,
                role=role
            )
            
            return {
                'member': member,
                'success': True,
                'message': f'User {username} added to project successfully'
            }
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to add member: {str(e)}")
    
    @staticmethod
    def add_project_member_by_user_id(project, user_id, role_id, user_profile):
        """
        Add a new member to the project using user UUID and role ID.
        
        Args:
            project: Project instance
            user_id: UUID of the user to add
            role_id: Role ID to assign to the member
            user_profile: UserProfile instance of the requester
            
        Returns:
            Dictionary with addition result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can add members")
        
        try:
            # Validate role ID
            from .models import ProjectRole
            role_info = ProjectRole.get_role_by_id(role_id)
            if not role_info:
                raise ValidationError(f"Invalid role ID: {role_id}")
            
            # Get user by UUID
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise ValidationError("User with this ID does not exist")
            
            target_profile = user.profile
            
            # Check if user is already a member
            if ProjectMember.objects.filter(project=project, profile=target_profile).exists():
                raise ValidationError("This user is already a member of this project")
            
            # Create project member
            member = ProjectMember.objects.create(
                project=project,
                profile=target_profile,
                role=role_info["value"]
            )
            
            return {
                'member': member,
                'success': True,
                'message': f'User {user.username} added to project successfully with role {role_info["name"]}'
            }
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to add member: {str(e)}")
    
    @staticmethod
    def remove_project_member(project, member_id, user_profile):
        """
        Remove a member from the project.
        
        Args:
            project: Project instance
            member_id: ID of the member to remove
            user_profile: UserProfile instance of the requester
            
        Returns:
            Dictionary with removal result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can remove members")
        
        try:
            member = project.members.get(id=member_id)
            
            # Prevent removing the owner
            if member.role == ProjectMember.Role.OWNER:
                raise ValidationError("Cannot remove project owner")
            
            member_username = member.profile.user.username
            member.delete()
            
            return {
                'success': True,
                'message': f'User {member_username} removed from project successfully'
            }
            
        except ProjectMember.DoesNotExist:
            raise ValidationError("Member not found")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to remove member: {str(e)}")

    @staticmethod
    def remove_project_member_by_user_id(project, user_id, user_profile):
        """
        Remove a member from the project using the user's UUID.

        Args:
            project: Project instance
            user_id: UUID of the user to remove
            user_profile: UserProfile instance of the requester

        Returns:
            Dictionary with removal result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can remove members")
        try:
            member = project.members.get(profile__user__id=user_id)

            if member.role == ProjectMember.Role.OWNER:
                raise ValidationError("Cannot remove project owner")

            member_username = member.profile.user.username
            member.delete()
            return {
                'success': True,
                'message': f'User {member_username} removed from project successfully'
            }
        except ProjectMember.DoesNotExist:
            raise ValidationError("Member not found")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to remove member: {str(e)}")
    
    @staticmethod
    def update_member_role(project, member_id, new_role, user_profile):
        """
        Update a member's role in the project.
        
        Args:
            project: Project instance
            member_id: ID of the member to update
            new_role: New role to assign
            user_profile: UserProfile instance of the requester
            
        Returns:
            Dictionary with update result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can update member roles")
        
        try:
            member = project.members.get(id=member_id)
            
            # Prevent changing owner role
            if member.role == ProjectMember.Role.OWNER:
                raise ValidationError("Cannot change project owner role")
            
            old_role = member.role
            member.role = new_role
            member.save()
            
            return {
                'member': member,
                'success': True,
                'message': f'Member role changed from {old_role} to {new_role}'
            }
            
        except ProjectMember.DoesNotExist:
            raise ValidationError("Member not found")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to update member role: {str(e)}")

    @staticmethod
    def update_member_role_by_user_id(project, user_id, new_role, user_profile):
        """
        Update a member's role using the user's UUID.

        Args:
            project: Project instance
            user_id: UUID of the user whose role to update
            new_role: New role to assign
            user_profile: UserProfile instance of the requester

        Returns:
            Dictionary with update result
        """
        if not ProjectService.check_owner_permission(project, user_profile):
            raise ValidationError("Only project owner can update member roles")
        try:
            member = project.members.get(profile__user__id=user_id)
            if member.role == ProjectMember.Role.OWNER:
                raise ValidationError("Cannot change project owner role")
            old_role = member.role
            member.role = new_role
            member.save()
            return {
                'member': member,
                'success': True,
                'message': f'Member role changed from {old_role} to {new_role}'
            }
        except ProjectMember.DoesNotExist:
            raise ValidationError("Member not found")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to update member role: {str(e)}")
    
    @staticmethod
    def get_project_stats(user_profile):
        """
        Get project statistics for a user.
        
        Args:
            user_profile: UserProfile instance
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Get user's projects (owned and joined)
            user_projects = ProjectService.get_user_projects(user_profile)
            
            # Calculate statistics
            total_projects = user_projects.count()
            total_members = ProjectMember.objects.filter(
                project__in=user_projects
            ).values('profile').distinct().count()
            
            # Projects by ownership
            owned_projects = user_projects.filter(owner_profile=user_profile)
            projects_by_owner = {
                'owned': owned_projects.count(),
                'joined': total_projects - owned_projects.count()
            }
            
            # Recent projects (last 5)
            recent_projects = user_projects.order_by('-created_at')[:5]
            
            return {
                'total_projects': total_projects,
                'total_members': total_members,
                'projects_by_owner': projects_by_owner,
                'recent_projects': recent_projects,
                'success': True
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to get project statistics: {str(e)}")
    
    @staticmethod
    def search_projects(query, user_profile):
        """
        Search projects by name or repository URL.
        
        Args:
            query: Search query string
            user_profile: UserProfile instance
            
        Returns:
            Dictionary with search results
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError("Search query must be at least 2 characters long")
        
        try:
            # Get user's accessible projects
            user_projects = ProjectService.get_user_projects(user_profile)
            
            # Apply search filter
            search_query = Q(
                Q(name__icontains=query) |
                Q(repo_url__icontains=query)
            )
            
            results = user_projects.filter(search_query)
            
            return {
                'projects': results,
                'count': results.count(),
                'success': True
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to search projects: {str(e)}")
    
    @staticmethod
    def get_project_by_id(project_id, user_profile):
        """
        Get project by ID with access check.
        
        Args:
            project_id: Project ID
            user_profile: UserProfile instance
            
        Returns:
            Project instance
        """
        try:
            project = Project.objects.get(id=project_id)
            
            if not ProjectService.check_project_access(project, user_profile):
                raise ValidationError("You do not have permission to access this project")
            
            return project
            
        except Project.DoesNotExist:
            raise ValidationError("Project not found")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to get project: {str(e)}")
    
    @staticmethod
    def update_project_branch(project, new_branch, user_profile):
        """
        Update project's default branch.
        
        Args:
            project: Project instance
            new_branch: New branch name
            user_profile: UserProfile instance
            
        Returns:
            Dictionary with update result
        """
        # Check if user has permission to update project settings
        # Allow owner and maintainer to update branch
        user_membership = project.members.filter(profile=user_profile).first()
        
        if not (project.owner_profile == user_profile or 
                (user_membership and user_membership.role in [ProjectMember.Role.OWNER, ProjectMember.Role.MAINTAINER])):
            raise ValidationError("Only project owner or maintainer can update the default branch")
        
        if not new_branch or len(new_branch.strip()) == 0:
            raise ValidationError("Branch name cannot be empty")
        
        try:
            old_branch = project.default_branch
            project.default_branch = new_branch.strip()
            project.save()
            
            return {
                'project': project,
                'success': True,
                'message': f'Default branch updated from "{old_branch}" to "{new_branch}"'
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to update branch: {str(e)}")
    
    @staticmethod
    def clone_repository_for_project(project, repo_url, branch=None):
        """
        Clone repository for a project.
        
        Args:
            project: Project instance
            repo_url: Git repository URL
            branch: Specific branch to clone (optional)
            
        Returns:
            Dictionary with clone result
        """
        try:
            # Validate repository URL
            if not GitUtils.validate_repo_url(repo_url):
                raise ValidationError("Invalid repository URL format")
            
            # Create repository directory path (prefer env overrides)
            repositories_root = os.getenv(
                'TNM_REPOSITORIES_DIR',
                os.path.join(settings.BASE_DIR, 'backend', 'tnm_repositories')
            )
            repo_dir = os.path.join(repositories_root, f"project_{project.id}")
            
            # Clone the repository
            clone_result = GitUtils.clone_repository(repo_url, repo_dir, branch)
            
            # Get available branches
            branches = GitUtils.get_repository_branches(repo_dir)
            current_branch = GitUtils.get_current_branch(repo_dir)
            
            # Update project with repository information
            project.repo_url = repo_url
            project.default_branch = current_branch
            project.save()
            
            return {
                'success': True,
                'message': 'Repository cloned successfully',
                'repository_path': repo_dir,
                'branches': branches,
                'current_branch': current_branch,
                'project': project
            }
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to clone repository: {str(e)}")
    
    # Simple in-memory cache for branch information
    _branch_cache = {}
    _cache_timeout = 300  # 5 minutes
    
    @staticmethod
    def get_project_branches(project):
        """
        Get all branches for a project's repository with caching.
        
        Args:
            project: Project instance
            
        Returns:
            Dictionary with branches information
        """
        try:
            import time
            
            # Check cache first
            cache_key = f"branches_{project.id}"
            current_time = time.time()
            
            if cache_key in ProjectService._branch_cache:
                cached_data, cache_time = ProjectService._branch_cache[cache_key]
                if current_time - cache_time < ProjectService._cache_timeout:
                    return cached_data
            
            repositories_root = os.getenv(
                'TNM_REPOSITORIES_DIR',
                os.path.join(settings.BASE_DIR, 'backend', 'tnm_repositories')
            )
            repo_dir = os.path.join(repositories_root, f"project_{project.id}")
            
            if not os.path.exists(repo_dir):
                raise ValidationError("Repository not found. Please clone the repository first.")
            
            branches = GitUtils.get_repository_branches(repo_dir)
            current_branch = GitUtils.get_current_branch(repo_dir)
            
            result = {
                'success': True,
                'branches': branches,
                'current_branch': current_branch,
                'repository_path': repo_dir
            }
            
            # Cache the result
            ProjectService._branch_cache[cache_key] = (result, current_time)
            
            return result
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to get repository branches: {str(e)}")
    
    @staticmethod
    def _clear_branch_cache(project_id):
        """Clear branch cache for a specific project."""
        cache_key = f"branches_{project_id}"
        if cache_key in ProjectService._branch_cache:
            del ProjectService._branch_cache[cache_key]
    
    @staticmethod
    def switch_project_branch(project, branch_name):
        """
        Switch to a different branch in the project's repository.
        
        Args:
            project: Project instance
            branch_name: Branch name to switch to
            
        Returns:
            Dictionary with switch result
        """
        try:
            repositories_root = os.getenv(
                'TNM_REPOSITORIES_DIR',
                os.path.join(settings.BASE_DIR, 'backend', 'tnm_repositories')
            )
            repo_dir = os.path.join(repositories_root, f"project_{project.id}")
            
            if not os.path.exists(repo_dir):
                raise ValidationError("Repository not found. Please clone the repository first.")
            
            # Switch to the specified branch
            switch_result = GitUtils.checkout_branch(repo_dir, branch_name)
            
            # Update project's default branch
            project.default_branch = branch_name
            project.save()
            
            # Clear branch cache for this project
            ProjectService._clear_branch_cache(project.id)

            return {
                'success': True,
                'message': f'Successfully switched to branch: {branch_name}',
                'current_branch': branch_name,
                'project': project
            }
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to switch branch: {str(e)}")

    @staticmethod
    def trigger_tnm_analysis_async(project: Project) -> None:
        """Trigger TNM FilesOwnership analysis asynchronously using project's default branch.
        Does not raise; any error is ignored.
        """
        def _run():
            try:
                # Late import to avoid circular deps
                from tnm_integration.services import TnmService
                branch = project.default_branch or 'main'

                # Resolve paths
                repos_root = getattr(settings, 'TNM_REPOSITORIES_DIR', os.getenv('TNM_REPOSITORIES_DIR', '/app/tnm_repositories'))
                output_root = getattr(settings, 'TNM_OUTPUT_DIR', os.getenv('TNM_OUTPUT_DIR', '/app/tnm_output'))
                repo_git_path = f"{repos_root}/project_{project.id}/.git"
                project_output_root = f"{output_root}/project_{project.id}"

                options = [
                    '--repository', repo_git_path,
                    '--developer-knowledge', f"{project_output_root}/DeveloperKnowledge.json",
                    '--files-ownership', f"{project_output_root}/FilesOwnership.json",
                    '--potential-ownership', f"{project_output_root}/PotentialAuthorship.json",
                    branch,
                ]

                service = TnmService(
                    java_path=getattr(settings, 'TNM_JAVA_PATH', 'java'),
                    tnm_jar=getattr(settings, 'TNM_JAR_PATH', '/app/tnm-cli.jar'),
                    run_script=getattr(settings, 'TNM_RUN_SCRIPT', None),
                )
                service.run_cli('FilesOwnershipMiner', options, args=[], timeout=getattr(settings, 'TNM_TIMEOUT', None))
            except Exception:
                # swallow
                return

        t = threading.Thread(target=_run, daemon=True)
        t.start()
    
    @staticmethod
    def validate_and_clone_repository(repo_url, user_profile):
        """
        Validate repository URL and get basic information without full clone.
        
        Args:
            repo_url: Git repository URL
            user_profile: UserProfile instance
            
        Returns:
            Dictionary with validation result
        """
        try:
            # Validate repository URL format
            if not GitUtils.validate_repo_url(repo_url):
                raise ValidationError("Invalid repository URL format. Please provide a valid Git repository URL.")
            
            # Use lightweight validation - just check if repository is accessible
            validation_result = GitUtils.validate_repository_access(repo_url)
            
            return {
                'success': True,
                'message': 'Repository validation successful',
                'branches': validation_result.get('branches', []),
                'default_branch': validation_result.get('default_branch', 'main'),
                'repo_url': repo_url
            }
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Repository validation failed: {str(e)}")
