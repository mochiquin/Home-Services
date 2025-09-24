from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import os
import shutil
from .services import TnmService
from common.git_utils import GitUtils
from projects.models import Project, ProjectMember
from common.response import ApiResponse
import logging


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_tnm(request):
	logger = logging.getLogger(__name__)
	logger.info("TNM run_tnm endpoint called", extra={
		'user': str(request.user),
		'has_data': bool(request.data)
	})
	"""
	Extract basic data for STC/MC-STC coordination calculations.
	Request JSON:
	{
		"data_type": "assignment_matrix" | "file_dependency" | "coordination_minimal",
		"safe_mode": true
	}
	"""
	payload = request.data or {}
	data_type = payload.get('data_type', 'coordination_minimal')
	
	# Validate data_type
	allowed_types = ['assignment_matrix', 'file_dependency', 'coordination_minimal']
	if data_type not in allowed_types:
		return ApiResponse.error(
			error_message=f'Invalid data_type. Must be one of: {", ".join(allowed_types)}',
			error_code="INVALID_DATA_TYPE"
		)

	# Authorization and project lookup
	project_id = payload.get('project_id')
	# Resolve project: by id or user's selected_project
	try:
		if project_id:
			project = Project.objects.get(id=project_id)
		else:
			project = getattr(request.user.profile, 'selected_project', None)
			if not project:
				return ApiResponse.error(
				error_message='project_id is required (or set selected_project first)',
				error_code="MISSING_PROJECT_ID"
			)
	except Project.DoesNotExist:
			return ApiResponse.not_found('Project not found')
	user_profile = request.user.profile
	membership = project.members.filter(profile=user_profile).first()
	if not (project.owner_profile == user_profile or (membership and membership.role in [ProjectMember.Role.OWNER, ProjectMember.Role.MAINTAINER])):
		return ApiResponse.forbidden('Only project owner or maintainer can run TNM')

	# Default safe_mode to True unless explicitly set false
	safe_mode = payload.get('safe_mode')
	safe_mode = True if safe_mode is None else bool(safe_mode)

	# Initialize options as empty list
	options = []

	# Convenience: allow passing project and auto-build options
	if project:
		# Decide path prefixes. Prefer explicit env/settings; otherwise fall back to container-standard paths
		docker_mode = os.getenv('TNM_DOCKER_MODE', 'false').lower() == 'true'
		if docker_mode:
			repos_root = os.getenv('TNM_REPOSITORIES_DIR', '/data/repositories')
			output_root = os.getenv('TNM_OUTPUT_DIR', '/data/output')
		else:
			# Default to container-local canonical paths if settings are not provided
			repos_root = getattr(settings, 'TNM_REPOSITORIES_DIR', os.getenv('TNM_REPOSITORIES_DIR', '/app/tnm_repositories'))
			output_root = getattr(settings, 'TNM_OUTPUT_DIR', os.getenv('TNM_OUTPUT_DIR', '/app/tnm_output'))
		repo_root_path = f"{repos_root}/project_{project.id}"
		repo_git_path = f"{repo_root_path}/.git"
		# Determine branch strictly from repository current branch
		try:
			branch = GitUtils.get_current_branch(repo_root_path)
		except Exception:
			branch = None
		if not branch:
			return ApiResponse.error('Current branch not found. Please use Switch Project Branch first.')
		# Sanitize branch for filesystem paths (e.g., feature/x -> feature_x)
		branch_fs = branch.replace('/', '_')
		# Output directory per project+branch to avoid collisions
		project_output_root = f"{output_root}/project_{project.id}_{branch_fs}"
		# Ensure output directory exists
		try:
			os.makedirs(project_output_root, exist_ok=True)
		except Exception:
			pass
		options = [
			'--repository', repo_git_path,
		]
		# Optional: only add excludes if explicitly allowed (some TNM builds do not support this option)
		if os.getenv('TNM_ALLOW_EXCLUDES', 'false').lower() == 'true':
			excludes = os.getenv('TNM_EXCLUDE_PATTERNS', 'docker/**,.github/**,docs/**').split(',')
			for p in filter(None, map(str.strip, excludes)):
				options += ['--exclude', p]
		# Append branch as the final arg
		options += [branch]

	# Map data types to TNM commands
	command_mapping = {
		'assignment_matrix': 'AssignmentMatrixMiner',
		'file_dependency': 'FileDependencyMatrixMiner', 
		'coordination_minimal': None  # Special case: run both essential miners
	}
	
	command = command_mapping.get(data_type)

	service = TnmService(
		java_path=getattr(settings, 'TNM_JAVA_PATH', 'java'),
		tnm_jar=getattr(settings, 'TNM_JAR_PATH', None),
		run_script=getattr(settings, 'TNM_RUN_SCRIPT', None),
	)
	# If safe_mode, prepare a temporary sparse workspace and point --repository to it
	temp_repo_dir = None
	if safe_mode and project and not payload.get('options'):
		try:
			allowed_suffixes = [
				'.py','.ts','.tsx','.js','.jsx','.java','.kt','.go','.rb','.php','.cs',
				'.c','.cpp','.h','.hpp','.rs','.swift','.m','.mm','.sql','.sh','.yaml',
				'.yml','.json','.xml','.gradle','.kts','.ini','.toml','.cfg','.conf',
			]
			excluded_dirs = ['docker', '.github', 'docs']
			temp_repo_dir, pruned_commit_sha = service.prepare_sparse_workspace(
				source_repo_path=repo_root_path,
				branch=branch,
				allowed_suffixes=allowed_suffixes,
				excluded_directories=excluded_dirs,
			)
			# Replace repository path to temp workspace
			for i in range(len(options)):
				if options[i] == '--repository' and i + 1 < len(options):
					options[i+1] = f"{temp_repo_dir}/.git"
			# Ensure TNM analyzes the pruned branch (CLI expects a branch name)
			if options:
				options[-1] = 'safe-mode-pruned'
		except Exception as e:
			logger.exception('safe_mode preparation failed')
			return ApiResponse.error('safe_mode preparation failed', data={'detail': str(e)})

	try:
		def _copy_outputs():
			try:
				import json
				docker_mode = os.getenv('TNM_DOCKER_MODE', 'false').lower() == 'true'
				# Prefer per-project output dir to be the authoritative location: if TNM_OUTPUT_DIR points elsewhere,
				# ensure we still pull from that root and the known fallback
				output_root_global = os.getenv('TNM_OUTPUT_DIR', '/data/output' if docker_mode else '/app/tnm_output')
				# Note: BASE_DIR already points to backend/; do not append another 'backend'
				fallback_result_dir = os.path.join(getattr(settings, 'BASE_DIR', '/app'), 'result')
				# 新增：检查项目输出目录中的result子目录
				project_result_dir = os.path.join(project_output_root, 'result')
				candidate_dirs = [project_result_dir, fallback_result_dir, output_root_global]
				
				filenames = [
					'idToUser.json', 'idToFile.json', 'idToUser', 'idToFile',
					'DeveloperKnowledge.json', 'FilesOwnership.json', 'PotentialAuthorship.json',
					'AssignmentMatrix.json', 'FileDependencyMatrix.json', 'CommitInfluenceGraph.json',
					'WorkTimeData.json', 'CoEditNetworks.json', 'ComplexityData.json',
					'PageRankResult.json', 'CoordinationMatrix.json', 'CongruenceResult.json',
					'AssignmentMatrix', 'FileDependencyMatrix', 'CoEdits', 'idToCommit',
				]
				os.makedirs(project_output_root, exist_ok=True)
				logger.info(f"Processing outputs from candidate dirs: {candidate_dirs} to {project_output_root}")
				copied_files = []
				
				for d in candidate_dirs:
					if os.path.isdir(d):
						logger.info(f"Checking directory: {d}")
						for name in filenames:
							src = os.path.join(d, name)
							if os.path.isfile(src):
								try:
									# Normalize target name: ensure .json extension
									target_name = name if name.endswith('.json') else f"{name}.json"
									dest = os.path.join(project_output_root, target_name)
									
									# 读取源文件内容
									with open(src, 'r', encoding='utf-8') as f:
										content = f.read().strip()
									
									# 检查内容是否已经是有效的JSON
									try:
										json_data = json.loads(content)
										# 如果已经是JSON，直接写入格式化的JSON
										with open(dest, 'w', encoding='utf-8') as f:
											json.dump(json_data, f, indent=2, ensure_ascii=False)
									except json.JSONDecodeError:
										# 如果不是JSON，尝试作为简单的字符串处理
										logger.warning(f"File {src} is not valid JSON, treating as plain text")
										with open(dest, 'w', encoding='utf-8') as f:
											json.dump({"content": content}, f, indent=2, ensure_ascii=False)
									
									copied_files.append(f"{src} -> {dest}")
									logger.info(f"Processed and converted: {name} -> {target_name}")
								except Exception as e:
									logger.warning(f"Failed to process {src}: {e}")
					else:
						logger.info(f"Directory not found: {d}")
				
				# 清理result子目录（如果存在的话）
				if os.path.isdir(project_result_dir) and copied_files:
					try:
						shutil.rmtree(project_result_dir)
						logger.info(f"Cleaned up result subdirectory: {project_result_dir}")
					except Exception as e:
						logger.warning(f"Failed to clean up result directory: {e}")
				
				logger.info(f"Total files processed: {len(copied_files)}")
			except Exception as e:
				logger.exception(f"Error in _copy_outputs: {e}")

		# Handle coordination_minimal: run only essential STC/MC-STC miners
		if data_type == 'coordination_minimal':
			results = []
			# Determine which repo path to use (temp safe_mode or original)
			repo_arg = None
			for i in range(len(options)):
				if options[i] == '--repository' and i + 1 < len(options):
					repo_arg = options[i+1]
					break
			if not repo_arg:
				repo_arg = repo_git_path
			branch_arg = options[-1] if options else branch
			
			# Only run essential miners for STC/MC-STC calculations
			essential_miners = ['AssignmentMatrixMiner', 'FileDependencyMatrixMiner']
			for cmd in essential_miners:
				proc = service.run_cli(
					cmd,
					['--repository', repo_arg],
					[branch_arg],
					cwd=project_output_root,
					timeout=getattr(settings, 'TNM_TIMEOUT', None)
				)
				results.append({
					'command': proc.args,
					'returncode': proc.returncode,
					'stdout': proc.stdout,
					'stderr': proc.stderr,
					'data_type': cmd.replace('Miner', '').lower()
				})
			_copy_outputs()
			ok = all(r['returncode'] == 0 for r in results)
			return ApiResponse.success({
				'data_type': data_type,
				'runs': results,
				'essential_data_extracted': ok
			}) if ok else ApiResponse.error('Essential data extraction failed', data={'runs': results})

		# Single data type extraction path
		if command:
			work_dir = project_output_root if project else getattr(settings, 'TNM_WORK_DIR', None)
			proc = service.run_cli(
				command,
				options,
				[],  # No additional args for data extraction
				cwd=work_dir,
				timeout=getattr(settings, 'TNM_TIMEOUT', None)
			)
			_copy_outputs()
			data = {
				'data_type': data_type,
				'command': proc.args,
				'returncode': proc.returncode,
				'stdout': proc.stdout,
				'stderr': proc.stderr,
			}
			if proc.returncode == 0:
				return ApiResponse.success(data=data)
			else:
				return ApiResponse.error(f'TNM {data_type} extraction failed', data=data)
		else:
			return ApiResponse.error(f'Unknown data_type: {data_type}')
	except Exception as e:
		logger.exception('TNM execution failed')
		return ApiResponse.error('TNM execution failed', data={'detail': str(e)})
	finally:
		if temp_repo_dir:
			try:
				shutil.rmtree(temp_repo_dir, ignore_errors=True)
			except Exception:
				pass




