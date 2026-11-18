from django.urls import path

from . import views

urlpatterns = [
    path('', views.care_today, name='care_today'),
    path('start/', views.care_start, name='care_start'),
    path('history/', views.care_history, name='care_history'),
    path('download/', views.care_download, name='care_download'),
    path('help/', views.care_help, name='care_help'),
    path('<int:pk>/delete/', views.entry_delete, name='entry_delete'),
    path('delete-all/', views.diary_delete, name='diary_delete'),
]
