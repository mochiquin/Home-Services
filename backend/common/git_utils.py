"""
Git utility functions for repository management.
Handles cloning, branch listing, and repository operations.
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from django.core.exceptions import ValidationError


class GitUtils:
    """Utility class for Git operations."""
    
    @staticmethod
    def clone_repository(repo_url: str, target_dir: str, branch: Optional[str] = None) -> Dict:
        """
        Clone a Git repository to the target directory.
        
        Args:
            repo_url: Git repository URL
            target_dir: Target directory path
            branch: Specific branch to clone (optional)
            
        Returns:
            Dictionary with clone result
        """
        try:
            # Ensure target directory exists
            os.makedirs(target_dir, exist_ok=True)
            
            # Prepare git clone command
            cmd = ['git', 'clone']
            if branch:
                cmd.extend(['-b', branch])
            cmd.extend([repo_url, target_dir])
            
            # Execute git clone
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                raise ValidationError(f"Git clone failed: {result.stderr}")
            
            return {
                'success': True,
                'message': f'Repository cloned successfully to {target_dir}',
                'path': target_dir
            }
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Git clone operation timed out")
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
            
            return sorted(unique_branches, key=lambda x: x['name'])
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Git operation timed out")
        except Exception as e:
            raise ValidationError(f"Failed to get repository branches: {str(e)}")
    
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
    def validate_repository_access(repo_url: str) -> Dict:
        """
        Lightweight validation of repository access without cloning.
        Uses git ls-remote to check repository accessibility and get branch info.
        
        Args:
            repo_url: Repository URL to validate
            
        Returns:
            Dictionary with validation result and basic info
        """
        try:
            # Use git ls-remote to get remote references without cloning
            cmd = ['git', 'ls-remote', '--heads', repo_url]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 seconds timeout
            )
            
            if result.returncode != 0:
                raise ValidationError(f"Repository not accessible: {result.stderr}")
            
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
                'default_branch': default_branch
            }
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Repository validation timeout - repository may be inaccessible")
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
