from django.urls import path
from . import views

app_name = 'requirements'

urlpatterns = [
    path('create/', views.create_requirement_view, name='create'),
    path('', views.list_requirements_view, name='list_requirements'),
    path('my/', views.my_requirements_view, name='my_requirements'),
    path('<int:requirement_id>/', views.requirement_detail_view, name='detail'),
    path('<int:requirement_id>/edit/', views.edit_requirement_view, name='edit'),
    path('<int:requirement_id>/download-pdf/', views.download_requirement_pdf_view, name='download_pdf'),
    # Admin management URLs
    path('admin/manage-departments/', views.manage_departments_view, name='manage_departments'),
    path('admin/manage-requirement-types/', views.manage_requirement_types_view, name='manage_requirement_types'),
]
