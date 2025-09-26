"""
API views for Git credential management.
"""

import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from .models import GitCredential
from .serializers import GitCredentialSerializer, GitCredentialCreateSerializer
from common.response import ApiResponse

logger = logging.getLogger(__name__)


class GitCredentialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Git credentials.
    
    Provides CRUD operations for Git authentication credentials.
    """
    
    serializer_class = GitCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter credentials to current user only."""
        return GitCredential.objects.filter(
            user_profile=self.request.user.profile
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return GitCredentialCreateSerializer
        return GitCredentialSerializer
    
    def list(self, request, *args, **kwargs):
        """List user's Git credentials."""
        try:
            user_profile = request.user.profile
            
            logger.info("Listing Git credentials", extra={
                'user_id': request.user.id
            })
            
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return ApiResponse.success(
                data=serializer.data,
                message="Git credentials retrieved successfully"
            )
            
        except Exception as e:
            logger.error("Failed to list Git credentials", extra={
                'user_id': request.user.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to retrieve Git credentials",
                error_code="CREDENTIALS_LIST_ERROR"
            )
    
    def create(self, request, *args, **kwargs):
        """Create a new Git credential."""
        try:
            user_profile = request.user.profile
            credential_type = request.data.get('credential_type')
            provider = request.data.get('provider', 'github')
            
            logger.info("Creating Git credential", extra={
                'user_id': request.user.id,
                'credential_type': credential_type,
                'provider': provider
            })
            
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                credential = serializer.save()
                
                logger.info("Git credential created successfully", extra={
                    'user_id': request.user.id,
                    'credential_id': credential.id,
                    'credential_type': credential_type,
                    'provider': provider
                })
                
                response_serializer = GitCredentialSerializer(credential)
                return ApiResponse.created(
                    data=response_serializer.data,
                    message="Git credential created successfully"
                )
            else:
                return ApiResponse.error(
                    error_message="Invalid credential data",
                    error_code="INVALID_CREDENTIAL_DATA",
                    data=serializer.errors
                )
                
        except ValidationError as e:
            logger.warning("Git credential creation failed - validation error", extra={
                'user_id': request.user.id,
                'error': str(e)
            })
            return ApiResponse.error(
                error_message=str(e),
                error_code="CREDENTIAL_VALIDATION_ERROR"
            )
        except Exception as e:
            logger.error("Git credential creation failed - system error", extra={
                'user_id': request.user.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to create Git credential",
                error_code="CREDENTIAL_CREATION_ERROR"
            )
    
    def update(self, request, *args, **kwargs):
        """Update a Git credential."""
        try:
            credential = self.get_object()
            
            logger.info("Updating Git credential", extra={
                'user_id': request.user.id,
                'credential_id': credential.id
            })
            
            # For updates, we need to re-create the credential with new data
            serializer = GitCredentialCreateSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                # Delete old credential and create new one
                old_credential_id = credential.id
                credential.delete()
                
                new_credential = serializer.save()
                
                logger.info("Git credential updated successfully", extra={
                    'user_id': request.user.id,
                    'old_credential_id': old_credential_id,
                    'new_credential_id': new_credential.id
                })
                
                response_serializer = GitCredentialSerializer(new_credential)
                return ApiResponse.success(
                    data=response_serializer.data,
                    message="Git credential updated successfully"
                )
            else:
                return ApiResponse.error(
                    error_message="Invalid credential data",
                    error_code="INVALID_CREDENTIAL_DATA",
                    data=serializer.errors
                )
                
        except ValidationError as e:
            return ApiResponse.error(
                error_message=str(e),
                error_code="CREDENTIAL_UPDATE_ERROR"
            )
        except Exception as e:
            logger.error("Git credential update failed", extra={
                'user_id': request.user.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to update Git credential",
                error_code="CREDENTIAL_UPDATE_ERROR"
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete a Git credential."""
        try:
            credential = self.get_object()
            credential_id = credential.id
            provider = credential.provider
            credential_type = credential.credential_type
            
            logger.info("Deleting Git credential", extra={
                'user_id': request.user.id,
                'credential_id': credential_id,
                'provider': provider,
                'credential_type': credential_type
            })
            
            credential.delete()
            
            logger.info("Git credential deleted successfully", extra={
                'user_id': request.user.id,
                'credential_id': credential_id
            })
            
            return ApiResponse.success(
                message=f"Git credential for {provider} deleted successfully"
            )
            
        except Exception as e:
            logger.error("Git credential deletion failed", extra={
                'user_id': request.user.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to delete Git credential",
                error_code="CREDENTIAL_DELETION_ERROR"
            )
    
    @action(detail=False, methods=['post'])
    def test_credential(self, request):
        """Test a Git credential by validating access to a repository."""
        try:
            user_profile = request.user.profile
            repo_url = request.data.get('repo_url')
            provider = request.data.get('provider', 'github')
            
            if not repo_url:
                return ApiResponse.error(
                    error_message="Repository URL is required",
                    error_code="MISSING_REPO_URL"
                )
            
            logger.info("Testing Git credential", extra={
                'user_id': request.user.id,
                'repo_url': repo_url,
                'provider': provider
            })
            
            # Import here to avoid circular imports
            from common.git_utils import GitUtils, GitPermissionError
            
            try:
                # Test repository access with user's credentials
                result = GitUtils.validate_repository_access(repo_url, user_profile)
                
                logger.info("Git credential test successful", extra={
                    'user_id': request.user.id,
                    'repo_url': repo_url,
                    'used_authentication': result.get('used_authentication', False)
                })
                
                return ApiResponse.success(
                    data={
                        'accessible': True,
                        'used_authentication': result.get('used_authentication', False),
                        'branches_count': len(result.get('branches', [])),
                        'default_branch': result.get('default_branch')
                    },
                    message="Repository access test successful"
                )
                
            except GitPermissionError as e:
                logger.warning("Git credential test failed - permission error", extra={
                    'user_id': request.user.id,
                    'repo_url': repo_url,
                    'error_type': e.error_type,
                    'error': str(e)
                })
                
                return ApiResponse.error(
                    error_message=e.message,
                    error_code=f"GIT_{e.error_type}",
                    status_code=status.HTTP_403_FORBIDDEN,
                    data={
                        'accessible': False,
                        'error_type': e.error_type,
                        'solution': e.solution
                    }
                )
                
        except Exception as e:
            logger.error("Git credential test failed - system error", extra={
                'user_id': request.user.id,
                'error': str(e)
            }, exc_info=True)
            return ApiResponse.internal_error(
                error_message="Failed to test Git credential",
                error_code="CREDENTIAL_TEST_ERROR"
            )
    
    @action(detail=False, methods=['get'])
    def providers(self, request):
        """Get list of supported Git providers."""
        providers = [
            {
                'name': 'github',
                'display_name': 'GitHub',
                'url_patterns': ['github.com'],
                'supports_tokens': True,
                'supports_ssh': True,
                'token_help': 'Create a Personal Access Token at https://github.com/settings/tokens'
            },
            {
                'name': 'gitlab',
                'display_name': 'GitLab',
                'url_patterns': ['gitlab.com'],
                'supports_tokens': True,
                'supports_ssh': True,
                'token_help': 'Create a Personal Access Token at https://gitlab.com/-/profile/personal_access_tokens'
            },
            {
                'name': 'bitbucket',
                'display_name': 'Bitbucket',
                'url_patterns': ['bitbucket.org'],
                'supports_tokens': True,
                'supports_ssh': True,
                'token_help': 'Create an App Password at https://bitbucket.org/account/settings/app-passwords/'
            }
        ]
        
        return ApiResponse.success(
            data=providers,
            message="Git providers retrieved successfully"
        )
