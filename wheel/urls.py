from django.urls import path

from . import views

urlpatterns = [
    path('', views.subscription_list, name='subscription_list'),
    path('add/', views.subscription_add, name='subscription_add'),
    path('upload/', views.statement_upload, name='statement_upload'),
    path('upload/review/', views.statement_review, name='statement_review'),
    path('screenshot/', views.screenshot_upload, name='screenshot_upload'),
]
