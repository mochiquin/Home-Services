import os
import subprocess
import shlex
from pathlib import Path
from typing import List, Optional


class TnmService:
	def __init__(self, java_path: str = 'java', tnm_jar: Optional[str] = None, run_script: Optional[str] = None):
		self.java_path = java_path
		# Fallback to env TNM_JAR_PATH when not provided via settings
		self.tnm_jar = tnm_jar or os.getenv('TNM_JAR_PATH')
		self.run_script = run_script
		# Docker exec mode support (prefer env when run_script not explicitly provided)
		docker_mode = os.getenv('TNM_DOCKER_MODE', 'false').lower() == 'true'
		self._docker_exec_prefix: Optional[list] = None
		if not self.run_script and docker_mode:
			container = os.getenv('TNM_CONTAINER_NAME', 'secuflow-tnm')
			jar_in_container = os.getenv('TNM_JAR_PATH', '/app/tnm-cli.jar')
			# docker exec <container> java -jar /app/tnm-cli.jar <command> ...
			self._docker_exec_prefix = ['docker', 'exec', container, self.java_path, '-jar', jar_in_container]

	def run_cli(self, command: str, options: List[str], args: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
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
		return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


