from django.urls import include, path

urlpatterns = [
    # Authentication and user management
    path('', include('accounts.urls')),
]


