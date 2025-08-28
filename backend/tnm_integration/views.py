from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .services import TnmService
from .models import TnmJob
from .serializers import TnmJobCreateSerializer, TnmJobSerializer
import boto3
import json


@api_view(['POST'])
@permission_classes([IsAdminUser])
def run_tnm(request):
	"""
	Trigger TNM CLI to analyze a Git repository.
	Request JSON:
	{
		"command": "AssignmentMatrixMiner",
		"options": ["--repository", "./repo/.git", "main"],
		"args": []
	}
	"""
	payload = request.data or {}
	command = payload.get('command')
	options = payload.get('options', [])
	args = payload.get('args', [])

	if not command:
		return Response({'error': 'command is required'}, status=status.HTTP_400_BAD_REQUEST)

	service = TnmService(
		java_path=getattr(settings, 'TNM_JAVA_PATH', 'java'),
		tnm_jar=getattr(settings, 'TNM_JAR_PATH', None),
		run_script=getattr(settings, 'TNM_RUN_SCRIPT', None),
	)
	try:
		proc = service.run_cli(command, options, args, cwd=getattr(settings, 'TNM_WORK_DIR', None), timeout=getattr(settings, 'TNM_TIMEOUT', None))
		return Response({
			'command': proc.args,
			'returncode': proc.returncode,
			'stdout': proc.stdout,
			'stderr': proc.stderr,
		}, status=status.HTTP_200_OK if proc.returncode == 0 else status.HTTP_400_BAD_REQUEST)
	except Exception as e:
		return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_job(request):
	serializer = TnmJobCreateSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({'error': 'invalid payload', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
	job: TnmJob = serializer.save(created_by=request.user, status='queued')
	# enqueue to SQS
	sqs_url = getattr(settings, 'TNM_SQS_QUEUE_URL', None)
	if not sqs_url:
		return Response({'error': 'TNM_SQS_QUEUE_URL not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
	client = boto3.client(
		'sqs',
		region_name=getattr(settings, 'AWS_REGION', None),
		endpoint_url=getattr(settings, 'AWS_ENDPOINT_URL', None),
	)
	msg = {
		'job_id': job.id,
		'repo_url': job.repo_url,
		'branch': job.branch,
		'command': job.command,
		'options': job.options,
		'args': job.args,
	}
	client.send_message(QueueUrl=sqs_url, MessageBody=json.dumps(msg))
	return Response({'id': job.id}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_detail(request, pk: int):
	try:
		job = TnmJob.objects.get(pk=pk)
	except TnmJob.DoesNotExist:
		return Response({'error': 'not found'}, status=status.HTTP_404_NOT_FOUND)
	return Response(TnmJobSerializer(job).data)


