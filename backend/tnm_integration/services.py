import subprocess
import shlex
from pathlib import Path
from typing import List, Optional


class TnmService:
	def __init__(self, java_path: str = 'java', tnm_jar: Optional[str] = None, run_script: Optional[str] = None):
		self.java_path = java_path
		self.tnm_jar = tnm_jar
		self.run_script = run_script

	def run_cli(self, command: str, options: List[str], args: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
		if self.run_script:
			cmd = [self.run_script, command] + options + args
		else:
			if not self.tnm_jar:
				raise ValueError('TNM jar path must be provided if run_script is not set')
			cmd = [self.java_path, '-jar', self.tnm_jar, command] + options + args

		return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


