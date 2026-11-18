from django.urls import path

from . import views

urlpatterns = [
    path('add/', views.todo_add, name='todo_add'),
    path('<int:pk>/toggle/', views.todo_toggle, name='todo_toggle'),
    path('<int:pk>/edit/', views.todo_edit, name='todo_edit'),
    path('<int:pk>/move/', views.todo_move, name='todo_move'),
    path('<int:pk>/delete/', views.todo_delete, name='todo_delete'),
    path('clear-done/', views.todo_clear_done, name='todo_clear_done'),
]
