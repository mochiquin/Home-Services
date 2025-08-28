import os
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

import boto3
from django.conf import settings
import django


def ensure_django():
	os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secuflow.settings')
	django.setup()


def upload_text_to_s3(bucket: str, key: str, content: str) -> str:
	s3 = boto3.client(
		's3',
		region_name=getattr(settings, 'AWS_REGION', None),
		endpoint_url=getattr(settings, 'AWS_ENDPOINT_URL', None),
	)
	s3.put_object(Bucket=bucket, Key=key, Body=content.encode('utf-8'), ContentType='text/plain')
	return f"s3://{bucket}/{key}"


def run_tnm(java_path: str, jar_path: str, command: str, options: list, args: list, cwd: str = None, timeout: int | None = None):
	cmd = [java_path, '-jar', jar_path, command] + options + args
	return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def process_message(msg_body: dict):
	from .models import TnmJob

	job_id = msg_body['job_id']
	repo_url = msg_body['repo_url']
	branch = msg_body.get('branch', 'main')
	command = msg_body['command']
	options = msg_body.get('options', [])
	args = msg_body.get('args', [])

	job = TnmJob.objects.filter(pk=job_id).first()
	if not job:
		return
	job.status = 'running'
	job.save(update_fields=['status', 'updated_at'])

	work_dir = tempfile.mkdtemp(prefix='tnm-')
	stdout_text = ''
	stderr_text = ''
	try:
		# shallow clone
		subprocess.check_call(['git', 'clone', '--depth', '1', '--branch', branch, repo_url, work_dir])
		# run TNM
		proc = run_tnm(
			java_path=getattr(settings, 'TNM_JAVA_PATH', 'java'),
			jar_path=getattr(settings, 'TNM_JAR_PATH'),
			command=command,
			options=['--repository', str(Path(work_dir) / '.git')] + options + [branch],
			args=args,
			cwd=getattr(settings, 'TNM_WORK_DIR', None),
			timeout=getattr(settings, 'TNM_TIMEOUT', None),
		)
		stdout_text = proc.stdout
		stderr_text = proc.stderr
		bucket = getattr(settings, 'TNM_S3_BUCKET', None)
		if bucket:
			stdout_url = upload_text_to_s3(bucket, f'tnm/jobs/{job_id}/stdout.txt', stdout_text)
			stderr_url = upload_text_to_s3(bucket, f'tnm/jobs/{job_id}/stderr.txt', stderr_text)
			job.stdout_url = stdout_url
			job.stderr_url = stderr_url
		job.status = 'succeeded' if proc.returncode == 0 else 'failed'
		if proc.returncode != 0:
			job.error = 'TNM returned non-zero code'
		job.save()
	except Exception as e:
		job.status = 'failed'
		job.error = str(e)
		job.save()
	finally:
		shutil.rmtree(work_dir, ignore_errors=True)


def main():
	ensure_django()
	queue_url = getattr(settings, 'TNM_SQS_QUEUE_URL', None)
	if not queue_url:
		raise RuntimeError('TNM_SQS_QUEUE_URL not configured')
	client = boto3.client(
		'sqs',
		region_name=getattr(settings, 'AWS_REGION', None),
		endpoint_url=getattr(settings, 'AWS_ENDPOINT_URL', None),
	)
	while True:
		resp = client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=20, VisibilityTimeout=300)
		messages = resp.get('Messages', [])
		for m in messages:
			body = json.loads(m['Body'])
			process_message(body)
			client.delete_message(QueueUrl=queue_url, ReceiptHandle=m['ReceiptHandle'])


if __name__ == '__main__':
	main()


