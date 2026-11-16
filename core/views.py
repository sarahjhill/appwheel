from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """The home page. The App Wheel will live here (stage 4)."""
    return render(request, 'core/home.html')
