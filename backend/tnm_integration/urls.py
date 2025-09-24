from django.urls import path
from .views import run_tnm

urlpatterns = [
	path('run/', run_tnm, name='tnm_run'),
]


