from django.urls import path
from . import views

app_name = 'approvals'

urlpatterns = [
    path('pending/', views.pending_approvals_view, name='pending_approvals'),
    path('pending-modifications/', views.pending_modifications_view, name='pending_modifications'),
    path('<int:approval_id>/approve/', views.approve_requirement_view, name='approve_requirement'),
]
