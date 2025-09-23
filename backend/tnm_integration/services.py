import os
import subprocess
import shlex
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
import logging


class TnmService:
	def __init__(self, java_path: str = 'java', tnm_jar: Optional[str] = None, run_script: Optional[str] = None):
		self.java_path = java_path
		# Fallback to env TNM_JAR_PATH when not provided via settings
		self.tnm_jar = tnm_jar or os.getenv('TNM_JAR_PATH')
		self.run_script = run_script
		self.logger = logging.getLogger(__name__)
		
		# Docker exec mode support (prefer env when run_script not explicitly provided)
		docker_mode = os.getenv('TNM_DOCKER_MODE', 'false').lower() == 'true'
		self._docker_exec_prefix: Optional[list] = None
		if not self.run_script and docker_mode:
			# Enable docker exec only when docker binary exists
			if shutil.which('docker'):
				container = os.getenv('TNM_CONTAINER_NAME', 'secuflow-tnm')
				jar_in_container = os.getenv('TNM_JAR_PATH', '/app/tnm-cli.jar')
				# docker exec <container> java -jar /app/tnm-cli.jar <command> ...
				self._docker_exec_prefix = ['docker', 'exec', container, self.java_path, '-jar', jar_in_container]
			else:
				self.logger.info('docker not found on PATH; falling back to direct java/jar mode')
		
		# Test log to verify logging configuration
		self.logger.info("TNM Service initialized", extra={
			'java_path': self.java_path,
			'tnm_jar': self.tnm_jar,
			'docker_mode': docker_mode,
			'has_run_script': bool(self.run_script),
			'has_docker_prefix': bool(self._docker_exec_prefix)
		})

	def run_cli(self, command: str, options: List[str], args: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
		self.logger.info("TNM run_cli start", extra={
			'command': command,
			'cli_options': options,
			'cli_args': args,
			'cwd': cwd,
			'timeout': timeout,
		})
		if self._docker_exec_prefix:
			cmd = self._docker_exec_prefix + [command] + options + args
		elif self.run_script:
			# Allow run_script to be a shell string or a list
			prefix = shlex.split(self.run_script) if isinstance(self.run_script, str) else list(self.run_script)
			cmd = prefix + [command] + options + args
		else:
			if not self.tnm_jar:
				raise ValueError('TNM jar path must be provided if run_script is not set')
			cmd = [self.java_path, '-jar', self.tnm_jar, command] + options + args

		# Note: when using docker exec, cwd is ignored by docker; paths should be absolute for the container
		stream = os.getenv('TNM_STREAM_LOG', 'false').lower() == 'true'
		if stream:
			# Stream stdout in real time to logger to observe long-running behavior
			self.logger.info('TNM streaming enabled')
			proc = subprocess.Popen(
				cmd,
				cwd=cwd,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				text=True,
			)
			stdout_buf = []
			try:
				while True:
					line = proc.stdout.readline()
					if not line and proc.poll() is not None:
						break
					if line:
						stdout_buf.append(line)
						self.logger.info(line.rstrip())
					# basic timeout check
					if timeout is not None and proc.poll() is None and sum(len(l) for l in stdout_buf) > 0:
						# leave actual timeout enforcement to external mechanisms for simplicity
						pass
			except Exception:
				proc.kill()
				raise
			return subprocess.CompletedProcess(cmd, proc.returncode or 0, ''.join(stdout_buf), '')
		else:
			proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
			self.logger.info("TNM run_cli finished", extra={
				'cmd': proc.args,
				'returncode': proc.returncode,
				'stdout_len': len(proc.stdout or ''),
				'stderr_len': len(proc.stderr or ''),
			})
			return proc


	def prepare_sparse_workspace(
		self,
		source_repo_path: str,
		branch: str,
		allowed_suffixes: Optional[List[str]] = None,
		excluded_directories: Optional[List[str]] = None,
	) -> tuple[str, Optional[str]]:
		"""Create a temporary sparse workspace from an existing local Git repo.

		- Clones the repo locally (no network), checks out the specified branch
		- Prunes working tree to only keep files with allowed suffixes
		- Removes excluded directories entirely
		- Returns path to the temporary repo root (that contains .git)
		"""
		allowed_suffixes = allowed_suffixes or [
			'.py','.ts','.tsx','.js','.jsx','.java','.kt','.go','.rb','.php','.cs',
			'.c','.cpp','.h','.hpp','.rs','.swift','.m','.mm','.sql','.sh',
			'.json','.xml','.gradle','.kts','.ini','.toml','.cfg','.conf',
		]
		excluded_directories = excluded_directories or ['docker', '.github', 'docs', 'playbooks', 'vagrant']

		work_dir = tempfile.mkdtemp(prefix='tnm-sparse-')
		self.logger.info('prepare_sparse_workspace: start', extra={
			'source_repo_path': source_repo_path,
			'branch': branch,
			'work_dir': work_dir,
			'allowed_suffixes_count': len(allowed_suffixes),
			'excluded_directories': excluded_directories,
		})
		# Validate inputs early
		try:
			if not source_repo_path or not os.path.isdir(source_repo_path):
				raise ValueError(f"source_repo_path not found: {source_repo_path}")
			repo_git_dir = os.path.join(source_repo_path, '.git')
			if not os.path.isdir(repo_git_dir):
				self.logger.warning('prepare_sparse_workspace: .git not found in source_repo_path', extra={'source_repo_path': source_repo_path})
		except Exception as e:
			self.logger.exception('prepare_sparse_workspace: input validation failed')
			raise

		def _run_git(args: list[str], step: str, timeout_sec: int = 60):
			cmd = ['git'] + args
			# Include step name in message for plain console formatters
			self.logger.info(f'git step start: {step}', extra={'git_step': step, 'git_cmd': cmd})
			try:
				proc = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout_sec)
				self.logger.info(f'git step done: {step}', extra={'git_step': step, 'returncode': proc.returncode, 'stdout_head': (proc.stdout or '')[:400]})
				return proc
			except subprocess.CalledProcessError as cpe:
				self.logger.error(f'git step failed: {step}', extra={'git_step': step, 'returncode': cpe.returncode, 'stdout': cpe.stdout, 'stderr': cpe.stderr})
				raise
			except subprocess.TimeoutExpired as te:
				self.logger.error(f'git step timeout: {step}', extra={'git_step': step, 'timeout': timeout_sec, 'git_cmd': te.cmd})
				raise

		# Local, shared clone without checkout to avoid copying blobs
		_run_git(['clone', '--local', '--shared', '--no-checkout', source_repo_path, work_dir], step='clone_no_checkout')
		# Checkout the desired branch to materialize working tree
		_run_git(['-C', work_dir, 'checkout', '-f', branch], step='checkout_branch')

		# Remove excluded directories from working tree (safe, does not alter history)
		# First, remove any top-level excluded dirs if present
		for ex in excluded_directories:
			p = os.path.join(work_dir, ex)
			if os.path.isdir(p):
				shutil.rmtree(p, ignore_errors=True)

		for root, dirs, files in os.walk(work_dir, topdown=True):
			# Skip the .git directory entirely
			if os.path.abspath(root) == os.path.abspath(os.path.join(work_dir, '.git')):
				continue
			# Delete and prune traversal into excluded directories
			to_delete_dirs = [d for d in dirs if d in excluded_directories]
			for d in to_delete_dirs:
				full = os.path.join(root, d)
				shutil.rmtree(full, ignore_errors=True)
			# Remove and skip symlinked directories
			kept_dirs = []
			for d in dirs:
				if d in excluded_directories or d == '.git':
					continue
				full = os.path.join(root, d)
				if os.path.islink(full):
					try:
						os.unlink(full)
					except Exception:
						pass
				else:
					kept_dirs.append(d)
			dirs[:] = kept_dirs
			# Delete files that do not match allowed suffixes
			for f in files:
				full = os.path.join(root, f)
				_, ext = os.path.splitext(f)
				# Remove symlinked files or files with non-allowed suffixes
				if os.path.islink(full) or ext.lower() not in allowed_suffixes:
					try:
						os.remove(full)
					except Exception:
						pass

		# Remove any gitlink (submodule) entries from index and working tree
		try:
			ls_proc = _run_git(['-C', work_dir, 'ls-files', '-s'], step='ls_files')
			for line in ls_proc.stdout.splitlines():
				parts = line.split('\t', 1)
				if len(parts) != 2:
					continue
				meta, relpath = parts
				mode = meta.split()[0] if meta else ''
				if mode == '160000':
					full = os.path.join(work_dir, relpath)
					try:
						os.remove(full)
					except IsADirectoryError:
						shutil.rmtree(full, ignore_errors=True)
					except Exception:
						pass
			# Ensure deletions are staged
			_run_git(['-C', work_dir, 'add', '-A'], step='add_all')
		except Exception:
			pass

		# Remove any empty directories left after pruning (bottom-up walk)
		for root, dirs, files in os.walk(work_dir, topdown=False):
			if os.path.abspath(root) == os.path.abspath(os.path.join(work_dir, '.git')):
				continue
			if not dirs and not files:
				try:
					os.rmdir(root)
				except Exception:
					pass


		# Preserve authorship: rewrite pruned branch history to drop excluded paths, keep original authors
		try:
			pruned_branch = 'safe-mode-pruned'
			# Create pruned branch from the original branch tip
			_run_git(['-C', work_dir, 'checkout', '-f', '-B', pruned_branch, branch], step='create_pruned_branch')
			# Optionally rewrite history to fully drop excluded paths (can be very expensive)
			enable_rewrite = os.getenv('TNM_SAFE_MODE_REWRITE_HISTORY', 'false').lower() == 'true'
			if enable_rewrite:
				self.logger.info('history rewrite enabled; running filter-branch (this may take minutes)')
				paths_to_remove = ' '.join(shlex.quote(d) for d in excluded_directories)
				if paths_to_remove:
					index_filter = f"git rm -r --cached --ignore-unmatch {paths_to_remove}"
					# Rewrite only the current branch (safe-mode-pruned)
					_run_git(['-C', work_dir, 'filter-branch', '-f', '--prune-empty', '--index-filter', index_filter, pruned_branch], step='filter_branch', timeout_sec=300)
			else:
				self.logger.info('history rewrite disabled; skipping filter-branch for speed')
		except Exception:
			# Non-fatal: if rewrite fails, we still have the pruned branch checked out
			pass

		self.logger.info('prepare_sparse_workspace: done', extra={'work_dir': work_dir})
		return work_dir, None

