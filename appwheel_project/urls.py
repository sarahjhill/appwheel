"""AppWheel URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # AppWheel's own account pages (delete my account)
    path('accounts/', include('accounts.urls')),
    # Sign up, log in, log out, password reset (django-allauth)
    path('accounts/', include('allauth.urls')),
    # The main app pages
    path('', include('core.urls')),
]
