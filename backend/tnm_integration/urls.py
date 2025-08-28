from django.urls import path
from .views import run_tnm, create_job, job_detail

urlpatterns = [
	path('run/', run_tnm, name='tnm_run'),
	path('jobs/', create_job, name='tnm_create_job'),
	path('jobs/<int:pk>/', job_detail, name='tnm_job_detail'),
]


