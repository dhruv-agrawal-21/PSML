from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from .models import Approval
from .forms import ApprovalActionForm
from apps.requirements.models import Requirement
from apps.audit.models import AuditLog
from apps.documents.models import Document
from apps.notifications.email_service import EmailNotificationService


@login_required(login_url='users:login')
def pending_approvals_view(request):
    """View pending approvals for current user"""
    user = request.user
    
    # Get pending approvals for this user
    pending_approvals = Approval.objects.filter(
        approver=user,
        status='pending'
    ).select_related('requirement', 'approver').order_by('-timestamp')
    
    # Get approved/rejected approvals for this user
    past_approvals = Approval.objects.filter(
        approver=user
    ).exclude(status='pending').select_related('requirement', 'approver').order_by('-timestamp')[:10]
    
    context = {
        'pending_approvals': pending_approvals,
        'past_approvals': past_approvals,
        'pending_count': pending_approvals.count(),
    }
    
    return render(request, 'approvals/pending_approvals.html', context)


@login_required(login_url='users:login')
def pending_modifications_view(request):
    """View pending modification requests for requirement creator"""
    user = request.user
    
    # Get all requirements where user is the creator and status is 'modification_requested'
    pending_modifications = Requirement.objects.filter(
        requested_by=user,
        status='modification_requested'
    ).order_by('-updated_date')
    
    # Get modification request details (latest request_modification approval)
    modification_requests = []
    for req in pending_modifications:
        mod_approval = Approval.objects.filter(
            requirement=req,
            status='request_modification'
        ).order_by('-timestamp').first()
        
        if mod_approval:
            modification_requests.append({
                'requirement': req,
                'approval': mod_approval,
                'approver': mod_approval.approver,
                'approver_level': mod_approval.get_approval_level_display(),
                'approver_level_value': mod_approval.approval_level,
                'comments': mod_approval.comments,
                'requested_date': mod_approval.timestamp,
                'additional_file': mod_approval.additional_document,
            })
    
    # Apply search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        modification_requests = [
            m for m in modification_requests
            if search_query.lower() in str(m['requirement'].id).lower() or
               search_query.lower() in m['requirement'].item_description.lower()
        ]
    
    # Apply level filter
    level_filter = request.GET.get('approver_level', '').strip()
    if level_filter:
        modification_requests = [
            m for m in modification_requests
            if str(m['approver_level_value']) == level_filter
        ]
    
    # Apply date filter
    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        from datetime import datetime
        try:
            filter_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            modification_requests = [
                m for m in modification_requests
                if m['requested_date'].date() >= filter_date
            ]
        except ValueError:
            pass
    
    context = {
        'page_title': 'Pending Modifications',
        'modification_requests': modification_requests,
        'pending_count': len(modification_requests),
        'search_query': search_query,
        'level_filter': level_filter,
        'date_from': date_from,
    }
    
    return render(request, 'approvals/pending_modifications.html', context)



@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def approve_requirement_view(request, approval_id):
    """Approve or reject a requirement"""
    approval = get_object_or_404(Approval, id=approval_id)
    requirement = approval.requirement
    
    # Check permission - only assigned approver can approve
    if approval.approver != request.user:
        messages.error(request, 'You are not authorized to approve this requirement.')
        return redirect('approvals:pending_approvals')
    
    # Check if already approved/rejected
    if approval.status != 'pending':
        messages.error(request, f'This approval has already been {approval.get_status_display().lower()}.')
        return redirect('approvals:pending_approvals')
    
    # Check if signed document is uploaded (required for approval, not for level 1 department head)
    signed_document = Document.objects.filter(
        approval=approval,
        is_signed=True
    ).first()
    
    if request.method == 'POST':
        form = ApprovalActionForm(request.POST, request.FILES, instance=approval)
        if form.is_valid():
            action = request.POST.get('action')
            comments = form.cleaned_data.get('comments')
            additional_doc = form.cleaned_data.get('additional_document')
            
            # For approval (not rejection/modification), check if document is uploaded
            # All approval levels (including department head) must upload a signed document
            if action == 'approved' and not signed_document:
                messages.error(request, 'Please upload a signed document before approving.')
                return redirect('documents:upload_signed_document', approval_id=approval.id)
            
            # Update approval
            approval.status = action
            approval.comments = comments
            if additional_doc:
                approval.additional_document = additional_doc
            approval.approved_date = timezone.now()
            approval.save()
            
            # Handle different actions
            if action == 'request_modification':
                # Request modification - send back to creator
                requirement.status = 'modification_requested'
                requirement.save()
                
                # Mark all documents as unsigned and reset status to pending
                Document.objects.filter(requirement=requirement).update(
                    is_signed=False,
                    status='pending'
                )
                
                # Delete all existing approvals (reset approval chain)
                Approval.objects.filter(requirement=requirement).exclude(id=approval.id).delete()
                
                # Create audit log
                AuditLog.objects.create(
                    requirement=requirement,
                    user=request.user,
                    action='modified',
                    details=f'Modification requested by {request.user.get_full_name()} ({request.user.get_role_display()}) - Level {approval.approval_level}. Comments: {comments}\n\nAll documents marked as unsigned. Approval chain will restart after modification.'
                )
                
                # Send email to creator with comments and optional file
                email_sent = EmailNotificationService.send_modification_request_notification(requirement, approval)
                
                if email_sent:
                    messages.success(request, 'Modification request sent to requirement creator. All documents marked as unsigned and approval chain will restart.')
                else:
                    messages.warning(request, 'Modification request recorded, but email notification failed. Documents marked as unsigned and approval chain will restart.')
            
            elif action == 'approved':
                # Create audit log
                AuditLog.objects.create(
                    requirement=requirement,
                    user=request.user,
                    action='approved',
                    details=f'{request.user.get_full_name()} ({request.user.get_role_display()}) approved. Comments: {comments}'
                )
                
                # Find next approval level and assign
                next_level = approval.approval_level + 1
                
                if next_level <= 4:
                    # Assign to next approver based on level
                    from apps.users.models import CustomUser
                    
                    next_approver_role = {
                        2: 'admin',
                        3: 'cfo',
                        4: 'ceo',
                    }.get(next_level)
                    
                    try:
                        next_approver = CustomUser.objects.get(role=next_approver_role)
                        
                        # Create next approval
                        next_approval = Approval.objects.create(
                            requirement=requirement,
                            approver=next_approver,
                            approval_level=next_level,
                            status='pending'
                        )
                        
                        # Update requirement next_approver
                        requirement.next_approver = next_approver
                        requirement.save()
                        
                        # Send email to next approver with signed document
                        email_sent = EmailNotificationService.send_approval_request_notification(
                            requirement, 
                            approval,
                            signed_document
                        )
                        
                        if email_sent:
                            messages.success(request, f'Requirement approved! Email sent to {next_approver.get_full_name()}.')
                        else:
                            messages.warning(request, f'Requirement approved and forwarded to {next_approver.get_full_name()}, but email notification failed.')
                        
                    except CustomUser.DoesNotExist:
                        messages.warning(request, 'Requirement approved but next approver not found.')
                else:
                    # All approvals complete
                    requirement.status = 'approved'
                    requirement.save()
                    
                    # Send final approval email to requester
                    email_sent = EmailNotificationService.send_final_approval_notification(requirement)
                    
                    if email_sent:
                        messages.success(request, 'Requirement fully approved! Notification sent to requester.')
                    else:
                        messages.warning(request, 'Requirement fully approved, but email notification failed.')
            
            else:  # rejected
                # Create audit log
                AuditLog.objects.create(
                    requirement=requirement,
                    user=request.user,
                    action='rejected',
                    details=f'{request.user.get_full_name()} ({request.user.get_role_display()}) rejected. Comments: {comments}'
                )
                
                requirement.status = 'rejected'
                requirement.save()
                
                # Send rejection email to requester
                email_sent = EmailNotificationService.send_rejection_notification(requirement, approval)
                
                if email_sent:
                    messages.success(request, 'Requirement rejected. Notification sent to requester.')
                else:
                    messages.warning(request, 'Requirement rejected, but email notification failed.')
            
            return redirect('approvals:pending_approvals')
    else:
        form = ApprovalActionForm(instance=approval)
    
    # Get all documents for this requirement
    all_documents = Document.objects.filter(requirement=requirement).order_by('approval__approval_level')
    
    context = {
        'approval': approval,
        'requirement': requirement,
        'form': form,
        'signed_document': signed_document,
        'all_documents': all_documents,
        'needs_document': not signed_document,
    }
    
    return render(request, 'approvals/approve_requirement.html', context)
