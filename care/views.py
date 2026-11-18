from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DiaryEntryForm, DownloadForm
from .models import CareDiary, DiaryEntry
from .pdf import diary_pdf


def _has_started(user):
    return CareDiary.objects.filter(user=user).exists()


@login_required
def care_start(request):
    """Explain what the care diary keeps, and let the user choose to start it."""
    if request.method == 'POST':
        CareDiary.objects.get_or_create(user=request.user)
        return redirect('care_today')
    return render(request, 'care/start.html')


@login_required
def care_today(request):
    """Write (or change) the diary entry for today, or for a past day."""
    if not _has_started(request.user):
        return redirect('care_start')

    today = date.today()
    try:
        day = date.fromisoformat(request.GET.get('date', '')) if request.GET.get('date') else today
    except ValueError:
        day = today
    if day > today:
        messages.info(request, 'You can only write about today or days that have passed.')
        day = today

    entry = DiaryEntry.objects.filter(user=request.user, date=day).first()
    if request.method == 'POST':
        form = DiaryEntryForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.date = day
            entry.save()
            messages.success(request, 'Saved to your diary.')
            return redirect(f"{request.path}?date={day.isoformat()}#saved")
    else:
        form = DiaryEntryForm(instance=entry)

    return render(request, 'care/today.html', {
        'form': form,
        'entry': entry,
        'day': day,
        'is_today': day == today,
        'yesterday': (day - timedelta(days=1)).isoformat(),
        'next_day': (day + timedelta(days=1)).isoformat() if day < today else None,
    })


@login_required
def care_history(request):
    """Past entries, newest first, with a red dot on days with a concern."""
    if not _has_started(request.user):
        return redirect('care_start')
    today = date.today()
    download_form = DownloadForm(initial={'start': today - timedelta(days=27), 'end': today})
    return render(request, 'care/history.html', {
        'entries': request.user.diary_entries.all(),
        'download_form': download_form,
    })


@login_required
def care_download(request):
    """Download the diary between two dates as a PDF."""
    form = DownloadForm(request.GET)
    if not form.is_valid():
        entries = request.user.diary_entries.all()
        return render(request, 'care/history.html', {'entries': entries, 'download_form': form})
    start, end = form.cleaned_data['start'], form.cleaned_data['end']
    entries = list(request.user.diary_entries.filter(date__range=(start, end)))
    response = HttpResponse(diary_pdf(request.user, entries, start, end), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="care-diary-{start}-to-{end}.pdf"'
    return response


@login_required
def care_help(request):
    """Where to go if care isn't right."""
    return render(request, 'care/help.html')


@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(DiaryEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'That diary entry has been deleted.')
        return redirect('care_history')
    return render(request, 'care/confirm_delete.html', {'entry': entry})


@login_required
def diary_delete(request):
    """Delete the whole care diary, and stop using it."""
    if request.method == 'POST' and request.POST.get('confirm') == 'DELETE':
        request.user.diary_entries.all().delete()
        CareDiary.objects.filter(user=request.user).delete()
        messages.success(request, 'Your care diary has been deleted.')
        return redirect('home')
    return render(request, 'care/confirm_delete_all.html', {
        'count': request.user.diary_entries.count(),
    })
