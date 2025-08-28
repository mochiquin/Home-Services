from django.db import models
from django.contrib.auth import get_user_model


class TnmJob(models.Model):
	STATUS_CHOICES = [
		('queued', 'Queued'),
		('running', 'Running'),
		('succeeded', 'Succeeded'),
		('failed', 'Failed'),
	]

	id = models.BigAutoField(primary_key=True)
	created_by = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL, related_name='tnm_jobs')
	repo_url = models.URLField()
	branch = models.CharField(max_length=255, default='main')
	command = models.CharField(max_length=255)
	options = models.JSONField(default=list, blank=True)
	args = models.JSONField(default=list, blank=True)
	status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='queued', db_index=True)
	stdout_url = models.URLField(blank=True, default='')
	stderr_url = models.URLField(blank=True, default='')
	result_url = models.URLField(blank=True, default='')
	error = models.TextField(blank=True, default='')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']


