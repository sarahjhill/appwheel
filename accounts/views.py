from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def delete_account(request):
    """Ask the user to confirm, then delete their account and everything
    linked to it. Required so people stay in control of their data."""
    if request.method == 'POST':
        if request.POST.get('confirm') == 'DELETE':
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, 'Your account and all your data have been deleted.')
            return redirect('account_login')
        messages.error(request, 'Please type DELETE in capital letters to confirm.')
    return render(request, 'accounts/delete_account.html')
