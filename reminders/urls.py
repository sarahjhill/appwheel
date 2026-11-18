from django.urls import path

from . import views

urlpatterns = [
    path('', views.reminder_list, name='reminder_list'),
    path('add/', views.reminder_add, name='reminder_add'),
    path('<int:pk>/edit/', views.reminder_edit, name='reminder_edit'),
    path('<int:pk>/done/', views.reminder_done, name='reminder_done'),
    path('<int:pk>/delete/', views.reminder_delete, name='reminder_delete'),
    path('checklist/<int:pk>/', views.checklist_tick, name='checklist_tick'),
]
