from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from . import ai

# Earlier questions and answers are kept in the session (not the database),
# so a follow-up like "what about Cardiff?" makes sense. Signing out clears them.
SESSION_KEY = 'ask_history'


@login_required
def ask_page(request):
    history = request.session.get(SESSION_KEY, [])
    error = ''
    question = ''
    if request.method == 'POST':
        question = request.POST.get('question', '')
        try:
            answer, sources = ai.ask(request.user, question, [
                {'role': turn['role'], 'content': turn['content']} for turn in history
            ])
        except ai.AskError as problem:
            error = str(problem)
        else:
            history = (history + [
                {'role': 'user', 'content': question.strip()},
                {'role': 'assistant', 'content': answer, 'sources': sources},
            ])[-ai.MAX_HISTORY:]
            request.session[SESSION_KEY] = history
            return redirect('ask_page')
    return render(request, 'assistant/ask.html', {
        'history': history,
        'suggestions': ai.SUGGESTIONS,
        'is_set_up': ai.is_set_up(),
        'error': error,
        'question': question,
    })


@login_required
def clear_history(request):
    if request.method == 'POST':
        request.session.pop(SESSION_KEY, None)
    return redirect('ask_page')
