"""
The to-do panel. Each action works two ways:
  - with JavaScript, the panel sends the change in the background and gets the
    updated list back, so you never leave the page you're on;
  - without JavaScript, the form posts normally and you're sent back to your page.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .context_processors import todo_panel
from .models import Todo

MAX_LENGTH = Todo._meta.get_field('text').max_length


def _clean(text):
    return (text or '').strip()[:MAX_LENGTH]


def _respond(request, announce=''):
    """Send back the updated list (for the panel), or go back to the page the user was on."""
    if request.headers.get('X-Requested-With') == 'fetch':
        context = todo_panel(request) | {'announce': announce}
        return render(request, 'todos/_list.html', context)
    next_url = request.POST.get('next') or request.GET.get('next') or '/'
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = '/'
    return redirect(next_url)


@login_required
@require_POST
def todo_add(request):
    text = _clean(request.POST.get('text'))
    if text:
        Todo.objects.create(user=request.user, text=text)
        return _respond(request, f'Added: {text}')
    return _respond(request, 'Type something to add first.')


@login_required
@require_POST
def todo_toggle(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    todo.done = not todo.done
    todo.done_at = timezone.now() if todo.done else None
    todo.save()
    return _respond(request, f'{"Done" if todo.done else "Not done"}: {todo.text}')


@login_required
def todo_edit(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    if request.method == 'POST':
        text = _clean(request.POST.get('text'))
        if text:
            todo.text = text
            todo.save()
        return _respond(request, f'Saved: {todo.text}')
    # Without JavaScript, editing happens on its own small page
    return render(request, 'todos/edit.html', {'todo': todo, 'next': request.GET.get('next', '/')})


@login_required
@require_POST
def todo_delete(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    text = todo.text
    todo.delete()
    return _respond(request, f'Deleted: {text}')


@login_required
@require_POST
def todo_clear_done(request):
    request.user.todos.filter(done=True).delete()
    return _respond(request, 'Cleared the done list.')


@login_required
@require_POST
def todo_move(request, pk):
    """Move a to-do between today's list and the backlog."""
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    if request.POST.get('to') == 'backlog':
        todo.in_backlog = True
        todo.save()
        return _respond(request, f'Moved to the backlog: {todo.text}')
    todo.in_backlog = False
    todo.day = timezone.localdate()
    todo.save()
    return _respond(request, f'Moved to today: {todo.text}')
