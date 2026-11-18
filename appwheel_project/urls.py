"""AppWheel URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # AppWheel's own account pages (delete my account)
    path('accounts/', include('accounts.urls')),
    # Sign up, log in, log out, password reset (django-allauth)
    path('accounts/', include('allauth.urls')),
    # My apps and subscriptions (the App Wheel)
    path('apps/', include('wheel.urls')),
    # Reminders: trials, renewals, appointments and prescriptions
    path('reminders/', include('reminders.urls')),
    # Care diary
    path('care/', include('care.urls')),
    # Help: emergency numbers and my important contacts
    path('help/', include('contacts.urls')),
    # The main app pages
    path('', include('core.urls')),
]
