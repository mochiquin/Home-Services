import json
import os
from django.utils import timezone
from django.db import transaction
from .models import Contributor, ProjectContributor
from .enums import FunctionalRole
from projects.models import Project
import logging

logger = logging.getLogger(__name__)


class TNMDataAnalysisService:
    """Service for analyzing TNM output data and storing contributor information."""
    
    @staticmethod
    def analyze_assignment_matrix(project: Project, tnm_output_dir: str, branch: str = None):
        """
        Analyze TNM AssignmentMatrix and idToUser data to extract contributor information.
        
        Args:
            project: Project instance
            tnm_output_dir: Directory containing TNM output files
            branch: Git branch analyzed (for metadata)
        
        Returns:
            dict: Analysis results with contributor count and statistics
        """
        try:
            # Load TNM output files
            id_to_user_path = os.path.join(tnm_output_dir, 'idToUser.json')
            id_to_file_path = os.path.join(tnm_output_dir, 'idToFile.json')
            assignment_matrix_path = os.path.join(tnm_output_dir, 'AssignmentMatrix.json')
            
            if not all(os.path.exists(p) for p in [id_to_user_path, assignment_matrix_path]):
                raise FileNotFoundError("Required TNM output files not found")
            
            # Load data
            with open(id_to_user_path, 'r', encoding='utf-8') as f:
                id_to_user = json.load(f)
            
            with open(assignment_matrix_path, 'r', encoding='utf-8') as f:
                assignment_matrix = json.load(f)
            
            # Optional: load file mapping for additional statistics
            id_to_file = {}
            if os.path.exists(id_to_file_path):
                with open(id_to_file_path, 'r', encoding='utf-8') as f:
                    id_to_file = json.load(f)
            
            return TNMDataAnalysisService._process_contributor_data(
                project, id_to_user, assignment_matrix, id_to_file, branch
            )
            
        except Exception as e:
            logger.error(f"Error analyzing TNM data for project {project.id}: {e}")
            raise
    
    @staticmethod
    def _process_contributor_data(project, id_to_user, assignment_matrix, id_to_file, branch):
        """Process and store contributor data from TNM analysis."""
        
        analysis_time = timezone.now()
        contributors_created = 0
        contributors_updated = 0
        
        with transaction.atomic():
            for user_id, email in id_to_user.items():
                try:
                    # Get or create Contributor
                    github_login = TNMDataAnalysisService._extract_username(email)
                    contributor, created = Contributor.objects.get_or_create(
                        github_login=github_login,
                        defaults={'email': email}
                    )
                    
                    if created:
                        contributors_created += 1
                    elif not contributor.email:
                        contributor.email = email
                        contributor.save()
                    
                    # Calculate statistics from assignment matrix
                    user_stats = TNMDataAnalysisService._calculate_user_statistics(
                        user_id, assignment_matrix, id_to_file
                    )
                    
                    # Suggest functional role based on activity patterns
                    suggested_role = TNMDataAnalysisService._suggest_functional_role(user_stats)
                    
                    # Update or create ProjectContributor
                    project_contributor, pc_created = ProjectContributor.objects.update_or_create(
                        project=project,
                        contributor=contributor,
                        defaults={
                            'tnm_user_id': user_id,
                            'files_modified': user_stats['files_count'],
                            'total_modifications': user_stats['total_modifications'],
                            'avg_modifications_per_file': user_stats['avg_modifications_per_file'],
                            'functional_role': suggested_role['role'],
                            'is_core_contributor': user_stats['total_modifications'] >= 100,
                            'role_confidence': suggested_role['confidence'],
                            'last_tnm_analysis': analysis_time,
                            'tnm_branch': branch or 'unknown',
                        }
                    )
                    
                    if not pc_created:
                        contributors_updated += 1
                        
                except Exception as e:
                    logger.error(f"Error processing contributor {email}: {e}")
                    continue
        
        return {
            'total_contributors': len(id_to_user),
            'contributors_created': contributors_created,
            'contributors_updated': contributors_updated,
            'analysis_time': analysis_time,
            'branch': branch,
        }
    
    @staticmethod
    def _extract_username(email):
        """Extract username from email address."""
        if '@' in email:
            username = email.split('@')[0]
            # Handle GitHub noreply emails
            if 'users.noreply.github.com' in email:
                # Extract actual username from noreply format
                parts = username.split('+')
                if len(parts) > 1:
                    return parts[1]  # Return the actual username part
                else:
                    return parts[0]  # Return the number part if no username
            return username
        return email
    
    @staticmethod
    def _calculate_user_statistics(user_id, assignment_matrix, id_to_file):
        """Calculate statistics for a user from assignment matrix."""
        user_data = assignment_matrix.get(user_id, {})
        
        files_count = len(user_data)
        total_modifications = sum(user_data.values())
        avg_modifications_per_file = total_modifications / files_count if files_count > 0 else 0
        
        # Calculate file type distribution
        file_types = {}
        for file_id, modifications in user_data.items():
            file_path = id_to_file.get(file_id, '')
            ext = TNMDataAnalysisService._get_file_extension(file_path)
            file_types[ext] = file_types.get(ext, 0) + modifications
        
        return {
            'files_count': files_count,
            'total_modifications': total_modifications,
            'avg_modifications_per_file': round(avg_modifications_per_file, 2),
            'file_types': file_types,
        }
    
    @staticmethod
    def _get_file_extension(file_path):
        """Get file extension from path."""
        if '.' in file_path:
            return file_path.split('.')[-1].lower()
        return 'no_ext'
    
    @staticmethod
    def _suggest_functional_role(user_stats):
        """Suggest functional role based on user statistics (MVP: Coder vs Reviewer)."""
        total_mods = user_stats['total_modifications']
        files_count = user_stats['files_count']
        avg_mods = user_stats['avg_modifications_per_file']
        
        # High activity suggests active coder
        if total_mods >= 100 and files_count >= 10:
            if avg_mods > 5:  # Deep modifications suggest coding
                return {'role': FunctionalRole.CODER, 'confidence': 0.8}
            else:  # Many files but shallow changes suggest reviewing
                return {'role': FunctionalRole.REVIEWER, 'confidence': 0.7}
        
        # Medium activity - likely coder
        elif total_mods >= 50:
            return {'role': FunctionalRole.CODER, 'confidence': 0.6}
        
        # Low activity - likely reviewer or occasional contributor  
        elif total_mods >= 10:
            return {'role': FunctionalRole.REVIEWER, 'confidence': 0.5}
        
        # Minimal activity - unclassified
        else:
            return {'role': FunctionalRole.UNCLASSIFIED, 'confidence': 0.3}
