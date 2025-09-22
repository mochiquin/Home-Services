from django.urls import include, path

urlpatterns = [
    path('', include('accounts.urls')),
    path('projects/', include('projects.urls')),
    path('tnm/', include('tnm_integration.urls')),
]


