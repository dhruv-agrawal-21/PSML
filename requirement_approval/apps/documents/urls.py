from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('upload/<int:approval_id>/', views.upload_signed_document, name='upload_signed_document'),
    path('download/<int:document_id>/', views.download_document, name='download_document'),
    path('requirement/<int:requirement_id>/', views.list_requirement_documents, name='list_requirement_documents'),
]
