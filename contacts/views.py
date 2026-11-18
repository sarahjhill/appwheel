from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PersonalContactForm
from .models import PersonalContact
from .numbers import CANT_SPEAK, EMERGENCY, NON_EMERGENCY


@login_required
def help_page(request):
    """Emergency numbers and my important contacts, one tap away."""
    return render(request, 'contacts/help.html', {
        'emergency': EMERGENCY,
        'non_emergency': NON_EMERGENCY,
        'cant_speak': CANT_SPEAK,
        'contacts': request.user.contacts.all(),
    })


@login_required
def contact_add(request):
    form = PersonalContactForm(request.POST or None, initial={'label': request.GET.get('label', 'other')})
    if request.method == 'POST' and form.is_valid():
        contact = form.save(commit=False)
        contact.user = request.user
        contact.save()
        messages.success(request, f'{contact.name} has been added.')
        return redirect('help_page')
    return render(request, 'contacts/contact_form.html', {'form': form})


@login_required
def contact_edit(request, pk):
    contact = get_object_or_404(PersonalContact, pk=pk, user=request.user)
    form = PersonalContactForm(request.POST or None, instance=contact)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{contact.name} has been updated.')
        return redirect('help_page')
    return render(request, 'contacts/contact_form.html', {'form': form, 'contact': contact})


@login_required
def contact_delete(request, pk):
    contact = get_object_or_404(PersonalContact, pk=pk, user=request.user)
    if request.method == 'POST':
        contact.delete()
        messages.success(request, f'{contact.name} has been removed.')
        return redirect('help_page')
    return render(request, 'contacts/contact_confirm_delete.html', {'contact': contact})
