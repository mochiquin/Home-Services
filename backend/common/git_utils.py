"""
Git utility functions for repository management.
Handles cloning, branch listing, and repository operations.
"""
import os
import subprocess
import shutil
import re
from pathlib import Path
from typing import List, Dict, Optional
from django.core.exceptions import ValidationError


class GitPermissionError(ValidationError):
    """Specific exception for Git permission issues."""
    
    def __init__(self, error_type: str, message: str, stderr: str = "", solution: str = ""):
        self.error_type = error_type
        self.stderr = stderr
        self.solution = solution
        super().__init__(message)


class GitUtils:
    """Utility class for Git operations."""
    
    @staticmethod
    def _analyze_git_error(stderr: str, repo_url: str = "") -> GitPermissionError:
        """
        Analyze Git error messages and return specific permission error type and solution.
        
        Args:
            stderr: Git command error output
            repo_url: Repository URL
            
        Returns:
            GitPermissionError with specific error type and solution
        """
        stderr_lower = stderr.lower()
        
        # Permission denied errors
        if any(phrase in stderr_lower for phrase in [
            'permission denied', 'access denied', 'permission denied (publickey)',
            'could not read from remote repository', 'please make sure you have the correct access rights'
        ]):
            if 'publickey' in stderr_lower or 'ssh' in stderr_lower:
                # Provide specific guidance for SSH issues
                if 'github.com' in repo_url:
                    solution = ("SSH access denied for GitHub. Please:\n"
                              "1. Generate SSH keys: ssh-keygen -t ed25519 -C \"your_email@example.com\"\n"
                              "2. Add public key to GitHub: Settings > SSH and GPG keys\n" 
                              "3. Or use HTTPS with Personal Access Token instead")
                elif 'gitlab.com' in repo_url:
                    solution = ("SSH access denied for GitLab. Please:\n"
                              "1. Generate SSH keys: ssh-keygen -t ed25519 -C \"your_email@example.com\"\n"
                              "2. Add public key to GitLab: User Settings > SSH Keys\n"
                              "3. Or use HTTPS with Personal Access Token instead")
                else:
                    solution = ("SSH access denied. Please:\n"
                              "1. Generate SSH keys if you don't have them\n"
                              "2. Add your public key to the Git provider\n"
                              "3. Or use HTTPS with authentication instead")
                    
                return GitPermissionError(
                    error_type="SSH_PERMISSION_DENIED",
                    message="SSH access denied, unable to access private repository",
                    stderr=stderr,
                    solution=solution
                )
            else:
                # Provide specific guidance for HTTPS issues
                if 'github.com' in repo_url:
                    solution = ("HTTPS access denied for GitHub. Please:\n"
                              "1. Create Personal Access Token: GitHub Settings > Developer settings > Personal access tokens\n"
                              "2. Grant 'repo' scope for private repositories\n"
                              "3. Configure the token in Secuflow: Account Settings > Git Credentials")
                elif 'gitlab.com' in repo_url:
                    solution = ("HTTPS access denied for GitLab. Please:\n"
                              "1. Create Personal Access Token: GitLab User Settings > Access Tokens\n"
                              "2. Grant 'read_repository' and 'write_repository' scopes\n"
                              "3. Configure the token in Secuflow: Account Settings > Git Credentials")
                else:
                    solution = ("HTTPS access denied. Please:\n"
                              "1. Create a Personal Access Token in your Git provider\n"
                              "2. Grant appropriate repository access permissions\n"
                              "3. Configure the token in Secuflow: Account Settings > Git Credentials")
                    
                return GitPermissionError(
                    error_type="HTTPS_PERMISSION_DENIED", 
                    message="HTTPS access denied, authentication may be required",
                    stderr=stderr,
                    solution=solution
                )
        
        # Repository not found or inaccessible
        if any(phrase in stderr_lower for phrase in [
            'repository not found', 'not found', 'does not exist',
            'repository does not exist', 'fatal: remote error'
        ]):
            solution = ("Repository not found. Please verify:\n"
                       "1. Repository URL is correct (check spelling and case)\n"
                       "2. Repository exists and is not deleted\n"
                       "3. You have access permissions to the repository\n"
                       "4. For private repositories, ensure you have proper authentication configured")
            
            return GitPermissionError(
                error_type="REPOSITORY_NOT_FOUND",
                message="Repository does not exist or is not accessible",
                stderr=stderr,
                solution=solution
            )
        
        # Network connection issues  
        if any(phrase in stderr_lower for phrase in [
            'failed to connect', 'connection timed out', 'network is unreachable',
            'temporary failure in name resolution', 'could not resolve host'
        ]):
            solution = ("Network connection failed. Please:\n"
                       "1. Check your internet connection\n"
                       "2. Verify the Git provider is accessible (try accessing in browser)\n"
                       "3. Check if you're behind a firewall or proxy\n"
                       "4. Try again in a few minutes in case of temporary network issues")
            
            return GitPermissionError(
                error_type="NETWORK_ERROR",
                message="Network connection failed",
                stderr=stderr,
                solution=solution
            )
        
        # Authentication failed
        if any(phrase in stderr_lower for phrase in [
            'authentication failed', 'invalid username or password',
            'bad credentials', 'unauthorized'
        ]):
            return GitPermissionError(
                error_type="AUTHENTICATION_FAILED",
                message="Authentication failed",
                stderr=stderr,
                solution="Please check your username and password, or use a valid personal access token"
            )
        
        # Branch not found
        if any(phrase in stderr_lower for phrase in [
            'remote branch', 'does not exist', "couldn't find remote ref"
        ]):
            return GitPermissionError(
                error_type="BRANCH_NOT_FOUND",
                message="Specified branch does not exist",
                stderr=stderr,
                solution="Please check if the branch name is correct or select another available branch"
            )
        
        # Timeout errors
        if 'timeout' in stderr_lower:
            return GitPermissionError(
                error_type="TIMEOUT",
                message="Operation timed out",
                stderr=stderr,
                solution="Repository may be large or network is slow, please try again later"
            )
        
        # Generic errors
        return GitPermissionError(
            error_type="UNKNOWN_ERROR",
            message=f"Git operation failed: {stderr}",
            stderr=stderr,
            solution="Please check repository URL and network connection, or contact administrator"
        )
    
    @staticmethod
    def get_git_credential_for_url(repo_url: str, user_profile=None):
        """
        Get appropriate Git credential for the given repository URL.
        
        Args:
            repo_url: Repository URL
            user_profile: UserProfile instance (optional)
            
        Returns:
            GitCredential instance or None
        """
        if not user_profile:
            return None
            
        try:
            from accounts.models import GitCredential
            
            # Determine provider from URL
            provider = 'github'
            if 'gitlab.com' in repo_url:
                provider = 'gitlab'
            elif 'bitbucket.org' in repo_url:
                provider = 'bitbucket'
            
            # Try to find matching credential
            credential = GitCredential.objects.filter(
                user_profile=user_profile,
                provider=provider,
                is_active=True
            ).first()
            
            return credential
        except Exception:
            return None
    
    @staticmethod
    def clone_repository(repo_url: str, target_dir: str, branch: Optional[str] = None, user_profile=None) -> Dict:
        """
        Clone a Git repository to the target directory.
        
        Args:
            repo_url: Git repository URL
            target_dir: Target directory path
            branch: Specific branch to clone (optional)
            user_profile: UserProfile for authentication (optional)
            
        Returns:
            Dictionary with clone result
            
        Raises:
            GitPermissionError: For specific Git permission/access issues
            ValidationError: For general validation errors
        """
        try:
            # Ensure target directory exists
            os.makedirs(target_dir, exist_ok=True)
            
            # Try to get authenticated URL if user profile is provided
            auth_url = repo_url
            credential = GitUtils.get_git_credential_for_url(repo_url, user_profile)
            if credential:
                try:
                    auth_url = credential.get_auth_url(repo_url)
                except Exception:
                    # If credential fails, fall back to original URL
                    auth_url = repo_url
            
            # Prepare git clone command
            cmd = ['git', 'clone']
            if branch:
                cmd.extend(['-b', branch])
            cmd.extend([auth_url, target_dir])
            
            # Execute git clone
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                # Analyze specific error type
                git_error = GitUtils._analyze_git_error(result.stderr, repo_url)
                raise git_error
            
            return {
                'success': True,
                'message': f'Repository cloned successfully to {target_dir}',
                'path': target_dir,
                'used_authentication': credential is not None
            }
            
        except subprocess.TimeoutExpired:
            raise GitPermissionError(
                error_type="TIMEOUT",
                message="Git clone operation timed out",
                solution="Repository may be large or network is slow, please try again later"
            )
        except GitPermissionError:
            raise  # Re-raise GitPermissionError as-is
        except Exception as e:
            raise ValidationError(f"Failed to clone repository: {str(e)}")
    
    @staticmethod
    def get_repository_branches(repo_path: str) -> List[Dict]:
        """
        Get all branches from a Git repository.
        
        Args:
            repo_path: Path to the Git repository
            
        Returns:
            List of branch information
        """
        try:
            if not os.path.exists(os.path.join(repo_path, '.git')):
                raise ValidationError("Not a valid Git repository")
            
            # Get all branches (local and remote)
            cmd = ['git', 'branch', '-a']
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise ValidationError(f"Failed to get branches: {result.stderr}")
            
            branches = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Parse branch information
                is_current = line.startswith('*')
                branch_name = line.replace('*', '').strip()
                
                # Skip HEAD references
                if 'HEAD' in branch_name:
                    continue
                
                # Clean up remote branch names
                if branch_name.startswith('remotes/origin/'):
                    branch_name = branch_name.replace('remotes/origin/', '')
                elif branch_name.startswith('remotes/'):
                    branch_name = branch_name.replace('remotes/', '')
                
                branches.append({
                    'name': branch_name,
                    'is_current': is_current,
                    'is_remote': 'remotes/' in line
                })
            
            # Remove duplicates and sort
            unique_branches = []
            seen = set()
            for branch in branches:
                if branch['name'] not in seen:
                    unique_branches.append(branch)
                    seen.add(branch['name'])
            
            # Batch get commit hashes for all branches
            if unique_branches:
                commit_hashes = GitUtils._get_batch_commit_hashes(repo_path, [b['name'] for b in unique_branches])
                
                # Add commit hash and branch_id to each branch
                for i, branch in enumerate(unique_branches):
                    commit_hash = commit_hashes.get(branch['name'])
                    branch['commit_hash'] = commit_hash
                    
                    # Generate unique branch ID using name + commit hash
                    import hashlib
                    branch_id_source = f"{branch['name']}:{commit_hash or 'unknown'}"
                    branch['branch_id'] = hashlib.md5(branch_id_source.encode()).hexdigest()
            
            return sorted(unique_branches, key=lambda x: x['name'])
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Git operation timed out")
        except Exception as e:
            raise ValidationError(f"Failed to get repository branches: {str(e)}")
    
    @staticmethod
    def _get_batch_commit_hashes(repo_path: str, branch_names: List[str]) -> Dict[str, str]:
        """
        Batch get commit hashes for multiple branches using a single git command.
        
        Args:
            repo_path: Path to the Git repository
            branch_names: List of branch names
            
        Returns:
            Dictionary mapping branch names to commit hashes
        """
        try:
            if not branch_names:
                return {}
            
            # Use git for-each-ref to get commit hashes for all branches at once
            cmd = ['git', 'for-each-ref', '--format=%(refname:short) %(objectname)', 'refs/heads/']
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Fallback to individual git rev-parse commands
                return GitUtils._get_individual_commit_hashes(repo_path, branch_names)
            
            commit_hashes = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2:
                        branch_name, commit_hash = parts
                        if branch_name in branch_names:
                            commit_hashes[branch_name] = commit_hash
            
            # Fill in missing branches with individual lookups
            missing_branches = [name for name in branch_names if name not in commit_hashes]
            if missing_branches:
                individual_hashes = GitUtils._get_individual_commit_hashes(repo_path, missing_branches)
                commit_hashes.update(individual_hashes)
            
            return commit_hashes
            
        except Exception:
            # Fallback to individual git rev-parse commands
            return GitUtils._get_individual_commit_hashes(repo_path, branch_names)
    
    @staticmethod
    def _get_individual_commit_hashes(repo_path: str, branch_names: List[str]) -> Dict[str, str]:
        """
        Fallback method to get commit hashes individually.
        
        Args:
            repo_path: Path to the Git repository
            branch_names: List of branch names
            
        Returns:
            Dictionary mapping branch names to commit hashes
        """
        commit_hashes = {}
        for branch_name in branch_names:
            try:
                cmd = ['git', 'rev-parse', branch_name]
                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    commit_hashes[branch_name] = result.stdout.strip()
            except Exception:
                continue
        
        return commit_hashes
    
    @staticmethod
    def get_current_branch(repo_path: str) -> str:
        """
        Get the current branch of a repository.
        
        Args:
            repo_path: Path to the Git repository
            
        Returns:
            Current branch name
        """
        try:
            cmd = ['git', 'branch', '--show-current']
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise ValidationError(f"Failed to get current branch: {result.stderr}")
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Git operation timed out")
        except Exception as e:
            raise ValidationError(f"Failed to get current branch: {str(e)}")
    
    @staticmethod
    def checkout_branch(repo_path: str, branch_name: str) -> Dict:
        """
        Checkout a specific branch in the repository.
        
        Args:
            repo_path: Path to the Git repository
            branch_name: Branch name to checkout
            
        Returns:
            Dictionary with checkout result
        """
        try:
            # First, fetch all remote branches
            fetch_cmd = ['git', 'fetch', '--all']
            subprocess.run(
                fetch_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Checkout the branch
            cmd = ['git', 'checkout', branch_name]
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise ValidationError(f"Failed to checkout branch '{branch_name}': {result.stderr}")
            
            return {
                'success': True,
                'message': f'Successfully checked out branch: {branch_name}',
                'current_branch': branch_name
            }
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Git operation timed out")
        except Exception as e:
            raise ValidationError(f"Failed to checkout branch: {str(e)}")
    
    @staticmethod
    def validate_repository_access(repo_url: str, user_profile=None) -> Dict:
        """
        Lightweight validation of repository access without cloning.
        Uses git ls-remote to check repository accessibility and get branch info.
        
        Args:
            repo_url: Repository URL to validate
            user_profile: UserProfile for authentication (optional)
            
        Returns:
            Dictionary with validation result and basic info
            
        Raises:
            GitPermissionError: For specific Git permission/access issues
            ValidationError: For general validation errors
        """
        try:
            # Try to get authenticated URL if user profile is provided
            auth_url = repo_url
            credential = GitUtils.get_git_credential_for_url(repo_url, user_profile)
            if credential:
                try:
                    auth_url = credential.get_auth_url(repo_url)
                except Exception:
                    # If credential fails, fall back to original URL
                    auth_url = repo_url
            
            # Use git ls-remote to get remote references without cloning
            cmd = ['git', 'ls-remote', '--heads', auth_url]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 seconds timeout
            )
            
            if result.returncode != 0:
                # Analyze specific error type
                git_error = GitUtils._analyze_git_error(result.stderr, repo_url)
                raise git_error
            
            # Parse branch information from ls-remote output
            branches = []
            default_branch = 'main'
            
            for line in result.stdout.strip().split('\n'):
                if line and '\trefs/heads/' in line:
                    branch_name = line.split('refs/heads/')[-1]
                    branches.append({
                        'name': branch_name,
                        'is_current': False
                    })
                    
                    # Determine default branch (prefer main, then master, then first branch)
                    if branch_name in ['main', 'master']:
                        default_branch = branch_name
            
            # If no branches found, use first branch or default
            if branches and default_branch not in [b['name'] for b in branches]:
                default_branch = branches[0]['name']
            
            # Mark default branch as current
            for branch in branches:
                if branch['name'] == default_branch:
                    branch['is_current'] = True
                    break
            
            return {
                'accessible': True,
                'branches': branches,
                'default_branch': default_branch,
                'used_authentication': credential is not None
            }
            
        except subprocess.TimeoutExpired:
            raise GitPermissionError(
                error_type="TIMEOUT",
                message="Repository validation timeout - repository may be inaccessible",
                solution="Please check your network connection or try again later"
            )
        except GitPermissionError:
            raise  # Re-raise GitPermissionError as-is
        except Exception as e:
            raise ValidationError(f"Repository validation failed: {str(e)}")

    @staticmethod
    def validate_repo_url(repo_url: str) -> bool:
        """
        Validate if the repository URL is valid.
        
        Args:
            repo_url: Repository URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        valid_prefixes = [
            'https://github.com/',
            'https://gitlab.com/',
            'https://bitbucket.org/',
            'git@github.com:',
            'git@gitlab.com:',
            'git@bitbucket.org:',
            'http://',
            'https://'
        ]
        
        return any(repo_url.startswith(prefix) for prefix in valid_prefixes)
    
    @staticmethod
    def cleanup_repository(repo_path: str) -> bool:
        """
        Remove a repository directory.
        
        Args:
            repo_path: Path to the repository to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
                return True
            return False
        except Exception:
            return False
