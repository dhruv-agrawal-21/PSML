from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils import timezone
from django.http import FileResponse
from .models import Requirement
from .forms import RequirementForm
from .pdf_utils import generate_requirement_pdf
from apps.approvals.models import Approval
from apps.users.models import CustomUser
from apps.audit.models import AuditLog
from apps.notifications.email_service import EmailNotificationService


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def create_requirement_view(request):
    """Create a new requirement"""
    # Only department users can create requirements
    if not request.user.is_department_user():
        messages.error(request, 'Only department users can create requirements.')
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        form = RequirementForm(request.POST)
        if form.is_valid():
            requirement = form.save(commit=False)
            requirement.requested_by = request.user
            requirement.department = request.user.department
            requirement.status = 'pending'
            
            # Find the department head as next approver
            try:
                dept_head = CustomUser.objects.get(
                    role='head',
                    department=request.user.department
                )
                requirement.next_approver = dept_head
            except CustomUser.DoesNotExist:
                messages.warning(request, 'Department head not found. Requirement created but no approver assigned.')
            
            requirement.save()
            
            # Create audit log
            AuditLog.objects.create(
                requirement=requirement,
                user=request.user,
                action='created',
                details=f'Requirement created by {request.user.get_full_name()}'
            )
            
            # Create initial approval record for department head
            if requirement.next_approver:
                Approval.objects.create(
                    requirement=requirement,
                    approver=requirement.next_approver,
                    approval_level=1,
                    status='pending'
                )
                
                # Send email notification with PDF to department head
                email_sent = EmailNotificationService.send_requirement_created_notification(requirement)
                if email_sent:
                    messages.success(request, f'Requirement {requirement.id} created successfully! Email sent to {requirement.next_approver.get_full_name()}.')
                else:
                    messages.warning(request, f'Requirement {requirement.id} created, but email notification failed.')
            else:
                messages.success(request, f'Requirement {requirement.id} created successfully!')
            
            return redirect('requirements:list_requirements')
    else:
        form = RequirementForm()
    
    return render(request, 'requirements/create_requirement.html', {'form': form})



@login_required(login_url='users:login')
def list_requirements_view(request):
    """List requirements based on user role"""
    user = request.user
    
    if user.is_department_user():
        # Department users see only their requirements
        requirements = Requirement.objects.filter(requested_by=user).order_by('-created_date')
    elif user.is_department_head():
        # Department heads see requirements from their department
        requirements = Requirement.objects.filter(
            department=user.department
        ).order_by('-created_date')
    elif user.is_admin_user() or user.is_cfo_user() or user.is_ceo_user():
        # Admins and executives see all requirements
        requirements = Requirement.objects.all().order_by('-created_date')
    else:
        requirements = Requirement.objects.none()
    
    # Search and filter
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    
    if search_query:
        requirements = requirements.filter(
            Q(item_description__icontains=search_query) |
            Q(justification__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    if status_filter:
        requirements = requirements.filter(status=status_filter)
    
    if priority_filter:
        requirements = requirements.filter(priority=priority_filter)
    
    context = {
        'requirements': requirements,
        'search_query': search_query,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'statuses': Requirement._meta.get_field('status').choices,
        'priorities': Requirement._meta.get_field('priority').choices,
    }
    
    return render(request, 'requirements/list_requirements.html', context)


@login_required(login_url='users:login')
def requirement_detail_view(request, requirement_id):
    """View requirement details and approval history"""
    requirement = get_object_or_404(Requirement, id=requirement_id)
    
    # Check permissions
    user = request.user
    if user.is_department_user() and requirement.requested_by != user:
        messages.error(request, 'You do not have permission to view this requirement.')
        return redirect('requirements:list_requirements')
    elif user.is_department_head() and requirement.department != user.department:
        messages.error(request, 'You do not have permission to view this requirement.')
        return redirect('requirements:list_requirements')
    
    # Get approvals
    approvals = Approval.objects.filter(requirement=requirement).order_by('approval_level')
    
    # Get audit logs
    audit_logs = AuditLog.objects.filter(requirement=requirement).order_by('-timestamp')
    
    # Get documents
    documents = requirement.documents.all().order_by('-uploaded_date')
    
    context = {
        'requirement': requirement,
        'approvals': approvals,
        'audit_logs': audit_logs,
        'documents': documents,
    }
    
    return render(request, 'requirements/detail_requirement.html', context)


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def edit_requirement_view(request, requirement_id):
    """Edit requirement - accessible by creator and current/past approvers"""
    requirement = get_object_or_404(Requirement, id=requirement_id)
    user = request.user
    
    # Check permissions - creator or any approver can edit
    is_creator = requirement.requested_by == user
    is_approver = Approval.objects.filter(
        requirement=requirement,
        approver=user
    ).exists()
    
    if not (is_creator or is_approver):
        messages.error(request, 'You do not have permission to edit this requirement.')
        return redirect('requirements:list_requirements')
    
    # Additional check: only creator can edit when status is modification_requested
    if requirement.status == 'modification_requested' and not is_creator:
        messages.error(request, 'Only the requirement creator can edit a requirement pending modifications.')
        return redirect('requirements:detail', requirement_id=requirement_id)
    
    if request.method == 'POST':
        form = RequirementForm(request.POST, instance=requirement)
        if form.is_valid():
            # Store original status to check if modification_requested
            was_modification_requested = requirement.status == 'modification_requested'
            
            # Track changes for audit log
            changes = {}
            for field in form.changed_data:
                old_value = getattr(requirement, field)
                new_value = form.cleaned_data[field]
                changes[field] = {
                    'from': str(old_value),
                    'to': str(new_value)
                }
            
            # Save the requirement
            requirement = form.save()
            
            # If modifying after modification request, reset approval chain
            if was_modification_requested:
                # Update status and modification flags
                requirement.status = 'pending'
                requirement.was_modified = True
                requirement.last_modified_date = timezone.now()
                
                # Find department head as next approver
                try:
                    dept_head = CustomUser.objects.get(
                        role='head',
                        department=requirement.department
                    )
                    requirement.next_approver = dept_head
                except CustomUser.DoesNotExist:
                    messages.error(request, 'Department head not found for this department. Changes saved but approval chain could not be reset.')
                    requirement.save()
                    return redirect('requirements:detail', requirement_id=requirement_id)
                
                requirement.save()
                
                # Delete all existing approvals (reset chain)
                Approval.objects.filter(requirement=requirement).delete()
                
                # Create new level 1 approval for department head
                Approval.objects.create(
                    requirement=requirement,
                    approver=dept_head,
                    approval_level=1,
                    status='pending'
                )
                
                # Create detailed audit log
                if changes:
                    change_details = '\n'.join([
                        f'{field}: {change["from"]} → {change["to"]}'
                        for field, change in changes.items()
                    ])
                    details = f'Requirement modified by {user.get_full_name()} in response to modification request\n\nChanges:\n{change_details}\n\nApproval chain restarted from Level 1 (Department Head)'
                else:
                    details = f'Requirement resubmitted by {user.get_full_name()} after modification request\n\nApproval chain restarted from Level 1 (Department Head)'
                
                # Send email notification to department head
                email_sent = EmailNotificationService.send_requirement_created_notification(requirement)
                
                success_msg = f'Requirement {requirement.id} updated and resubmitted successfully! Approval process has restarted from Department Head.'
                if not email_sent:
                    success_msg += ' (Email notification failed - please notify approver manually)'
                
                messages.success(request, success_msg)
            else:
                # Normal edit - not a modification response
                # Ensure requirement is saved (form.save() already saved, but be explicit)
                requirement.save()
                
                if changes:
                    change_details = '\n'.join([
                        f'{field}: {change["from"]} → {change["to"]}'
                        for field, change in changes.items()
                    ])
                    details = f'Requirement modified by {user.get_full_name()} ({user.get_role_display()})\n\nChanges:\n{change_details}'
                else:
                    details = f'Requirement viewed/accessed by {user.get_full_name()}'
                
                messages.success(request, f'Requirement {requirement.id} updated successfully!')
            
            # Create audit log
            AuditLog.objects.create(
                requirement=requirement,
                user=user,
                action='modified',
                details=details
            )
            
            return redirect('requirements:detail', requirement_id=requirement_id)
    else:
        form = RequirementForm(instance=requirement)
    
    context = {
        'form': form,
        'requirement': requirement,
        'page_title': f'Edit Requirement #{requirement.id}',
    }
    
    return render(request, 'requirements/edit_requirement.html', context)


@login_required(login_url='users:login')
def my_requirements_view(request):
    """Alias for list_requirements for department users"""
    return list_requirements_view(request)


@login_required(login_url='users:login')
def download_requirement_pdf_view(request, requirement_id):
    """Download requirement as PDF"""
    requirement = get_object_or_404(Requirement, id=requirement_id)
    
    # Check permissions
    user = request.user
    if user.is_department_user() and requirement.requested_by != user:
        messages.error(request, 'You do not have permission to download this requirement.')
        return redirect('requirements:list_requirements')
    elif user.is_department_head() and requirement.department != user.department:
        messages.error(request, 'You do not have permission to download this requirement.')
        return redirect('requirements:list_requirements')
    
    # Generate PDF
    buffer = generate_requirement_pdf(requirement)
    response = FileResponse(buffer, as_attachment=True, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Requirement_{requirement.id}.pdf"'
    
    return response


