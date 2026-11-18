from django.urls import path

from . import views

urlpatterns = [
    path('', views.subscription_list, name='subscription_list'),
    path('add/', views.subscription_add, name='subscription_add'),
    path('<int:pk>/edit/', views.subscription_edit, name='subscription_edit'),
    path('<int:pk>/remove/', views.subscription_delete, name='subscription_delete'),
    path('<int:pk>/cancel/', views.cancel_help, name='cancel_help'),
    path('<int:pk>/cancelled/', views.mark_cancelled, name='mark_cancelled'),
    path('<int:pk>/active/', views.mark_active, name='mark_active'),
    path('<int:pk>/refund/', views.refund_request, name='refund_request'),
    path('<int:pk>/safety/', views.safety_guides, name='safety_guides'),
    path('upload/', views.statement_upload, name='statement_upload'),
    path('upload/review/', views.statement_review, name='statement_review'),
    path('screenshot/', views.screenshot_upload, name='screenshot_upload'),
]
