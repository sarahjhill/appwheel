from django.urls import path

from . import views

urlpatterns = [
    path('', views.help_page, name='help_page'),
    path('contacts/add/', views.contact_add, name='contact_add'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/remove/', views.contact_delete, name='contact_delete'),
]
