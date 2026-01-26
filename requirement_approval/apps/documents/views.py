from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import FileResponse, Http404
from django.utils import timezone
from .models import Document
from .forms import DocumentUploadForm
from apps.requirements.models import Requirement
from apps.approvals.models import Approval
from apps.audit.models import AuditLog
import os


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def upload_signed_document(request, approval_id):
    """Upload signed document for a specific approval"""
    approval = get_object_or_404(Approval, id=approval_id)
    requirement = approval.requirement
    
    # Check permission - only the assigned approver can upload
    if approval.approver != request.user:
        messages.error(request, 'You are not authorized to upload documents for this approval.')
        return redirect('approvals:pending_approvals')
    
    # Check if approval is still pending
    if approval.status != 'pending':
        messages.error(request, 'This approval has already been processed.')
        return redirect('approvals:pending_approvals')
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.requirement = requirement
            document.approval = approval
            document.uploaded_by = request.user
            document.document_type = 'signed'
            document.is_signed = True
            
            # Generate filename
            original_filename = request.FILES['file'].name
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            document.file_name = f'REQ{requirement.id}_Approval_Level{approval.approval_level}_{timestamp}_{original_filename}'
            
            document.save()
            
            # Create audit log
            AuditLog.objects.create(
                requirement=requirement,
                user=request.user,
                action='uploaded',
                details=f'Signed document uploaded by {request.user.get_full_name()} for approval level {approval.approval_level}'
            )
            
            messages.success(request, 'Signed document uploaded successfully!')
            return redirect('approvals:approve_requirement', approval_id=approval.id)
    else:
        form = DocumentUploadForm()
    
    context = {
        'form': form,
        'approval': approval,
        'requirement': requirement,
    }
    
    return render(request, 'documents/upload_document.html', context)


@login_required(login_url='users:login')
def download_document(request, document_id):
    """Download a document"""
    document = get_object_or_404(Document, id=document_id)
    requirement = document.requirement
    
    # Check permissions
    user = request.user
    has_permission = False
    
    # Requester can download their own requirement documents
    if requirement.requested_by == user:
        has_permission = True
    # Department head can download from their department
    elif user.is_department_head() and requirement.department == user.department:
        has_permission = True
    # Admins and executives can download all
    elif user.is_admin_user() or user.is_cfo_user() or user.is_ceo_user():
        has_permission = True
    # Approvers in the chain can download
    elif Approval.objects.filter(requirement=requirement, approver=user).exists():
        has_permission = True
    
    if not has_permission:
        messages.error(request, 'You do not have permission to download this document.')
        return redirect('users:dashboard')
    
    try:
        # Open and return file
        response = FileResponse(document.file.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
        return response
    except Exception as e:
        messages.error(request, f'Error downloading document: {str(e)}')
        return redirect('requirements:detail', requirement_id=requirement.id)


@login_required(login_url='users:login')
def list_requirement_documents(request, requirement_id):
    """List all documents for a requirement"""
    requirement = get_object_or_404(Requirement, id=requirement_id)
    
    # Check permissions
    user = request.user
    if user.is_department_user() and requirement.requested_by != user:
        messages.error(request, 'You do not have permission to view these documents.')
        return redirect('requirements:list_requirements')
    elif user.is_department_head() and requirement.department != user.department:
        messages.error(request, 'You do not have permission to view these documents.')
        return redirect('requirements:list_requirements')
    
    documents = Document.objects.filter(requirement=requirement).order_by('-uploaded_date')
    
    context = {
        'requirement': requirement,
        'documents': documents,
    }
    
    return render(request, 'documents/list_documents.html', context)
