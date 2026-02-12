from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_list_view, name='list_audit'),
    path('<int:audit_id>/pdf/', views.audit_pdf_view, name='audit_pdf'),
]
