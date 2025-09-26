#!/usr/bin/env python
import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeservices.settings')
django.setup()

from accounts.models import User

# Create superuser
username = 'admin'
email = 'admin@homeservices.com'
password = 'admin123456'

if not User.objects.filter(username=username).exists():
    user = User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser created successfully!')
    print(f'Username: {username}')
    print(f'Email: {email}')
    print(f'Password: {password}')
else:
    print(f'Superuser {username} already exists!')