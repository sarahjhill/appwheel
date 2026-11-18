from django.urls import path

from . import views

urlpatterns = [
    path('', views.ask_page, name='ask_page'),
    path('clear/', views.clear_history, name='ask_clear'),
]
