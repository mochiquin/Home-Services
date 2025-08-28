from rest_framework import serializers
from .models import TnmJob


class TnmJobCreateSerializer(serializers.ModelSerializer):
	class Meta:
		model = TnmJob
		fields = ['repo_url', 'branch', 'command', 'options', 'args']


class TnmJobSerializer(serializers.ModelSerializer):
	class Meta:
		model = TnmJob
		fields = ['id', 'repo_url', 'branch', 'command', 'options', 'args', 'status', 'stdout_url', 'stderr_url', 'result_url', 'error', 'created_at', 'updated_at']


