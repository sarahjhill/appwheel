def todo_panel(request):
    """Gives every page the to-do list, for the panel on the right."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    from django.utils import timezone
    today = timezone.localdate()
    todos = list(request.user.todos.all())
    # The page to come back to when JavaScript is off
    next_url = request.POST.get('next') if request.path.startswith('/todos/') else request.get_full_path()
    return {
        'todo_next': next_url or '/',
        'todo_items': [todo for todo in todos if not todo.done and not todo.is_backlog(today)],
        'todo_backlog': [todo for todo in todos if todo.is_backlog(today)],
        'todo_done': [todo for todo in todos if todo.done][:20],
    }
