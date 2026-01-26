from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Q, Count
from datetime import timedelta
from django.utils import timezone
from .forms import CustomAuthenticationForm
from .models import CustomUser
from apps.audit.models import AuditLog


@require_http_methods(["GET", "POST"])
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('users:dashboard')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})


@login_required(login_url='users:login')
def dashboard_view(request):
    """Role-based dashboard view with dynamic counts"""
    from apps.requirements.models import Requirement
    from apps.approvals.models import Approval
    
    user = request.user
    context = {
        'user': user,
        'role': user.get_role_display(),
        'department': user.get_department_display(),
    }
    
    # Add role-specific context and counts
    if user.role == 'user':
        context['page_title'] = 'My Requirements'
        # Count user's requirements by status
        context['pending_count'] = Requirement.objects.filter(requested_by=user, status='pending').count()
        context['approved_count'] = Requirement.objects.filter(requested_by=user, status='approved').count()
        
    elif user.role == 'head':
        context['page_title'] = 'Pending Approvals'
        # Count pending approvals for this head
        context['pending_count'] = Approval.objects.filter(approver=user, status='pending').count()
        context['approved_count'] = Approval.objects.filter(approver=user, status='approved').count()
        context['rejected_count'] = Approval.objects.filter(approver=user, status='rejected').count()
        
    elif user.role == 'admin':
        context['page_title'] = 'System Overview'
        # Count pending approvals for admin
        context['pending_count'] = Approval.objects.filter(approver=user, status='pending').count()
        context['total_requirements'] = Requirement.objects.count()
        
    elif user.role == 'cfo':
        context['page_title'] = 'CFO Dashboard'
        # Count high value approvals pending for CFO
        context['pending_count'] = Approval.objects.filter(approver=user, status='pending').count()
        # Calculate total budget of all approved requirements
        total_budget = Requirement.objects.filter(status='approved').aggregate(total=Sum('estimated_cost'))['total'] or 0
        context['total_budget'] = total_budget
        
    elif user.role == 'ceo':
        context['page_title'] = 'CEO Dashboard'
        # Count final approvals pending for CEO
        context['pending_count'] = Approval.objects.filter(approver=user, status='pending').count()
        # Count critical priority items
        context['critical_count'] = Requirement.objects.filter(priority='critical', status='pending').count()
        # Calculate total investments (all approved requirements)
        total_investments = Requirement.objects.filter(status='approved').aggregate(total=Sum('estimated_cost'))['total'] or 0
        context['total_investments'] = total_investments
    
    return render(request, 'users/dashboard.html', context)


@require_http_methods(["POST"])
def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('users:login')


@login_required(login_url='users:login')
def profile_view(request):
    """User profile view"""
    return render(request, 'users/profile.html', {'user': request.user})


@login_required(login_url='users:login')
def department_stats_view(request):
    """Department head statistics and analytics dashboard"""
    from apps.requirements.models import Requirement
    from apps.approvals.models import Approval
    
    user = request.user
    
    # Check if user is department head
    if not user.is_department_head():
        return redirect('users:dashboard')
    
    # Get requirements in user's department
    dept_requirements = Requirement.objects.filter(department=user.department)
    
    # Recent requirements in department
    recent_requirements = dept_requirements.select_related(
        'requested_by'
    ).order_by('-created_date')[:10]
    
    # Approvals by status for this department
    dept_approvals = Approval.objects.filter(
        requirement__department=user.department
    )
    
    approval_breakdown = {
        'pending': dept_approvals.filter(status='pending').count(),
        'approved': dept_approvals.filter(status='approved').count(),
        'rejected': dept_approvals.filter(status='rejected').count(),
    }
    
    # Top requesters in department
    top_requesters = dept_requirements.values(
        'requested_by__first_name',
        'requested_by__last_name'
    ).annotate(count=Count('id')).order_by('-count')[:5]
    
    # Stats
    stats = {
        'total_requirements': dept_requirements.count(),
        'pending_count': dept_requirements.filter(status='pending').count(),
        'approved_count': dept_requirements.filter(status='approved').count(),
        'rejected_count': dept_requirements.filter(status='rejected').count(),
        'total_cost': dept_requirements.filter(status='approved').aggregate(
            total=Sum('estimated_cost')
        )['total'] or 0,
    }
    
    context = {
        'page_title': f"{user.get_department_display()} - Department Statistics",
        'stats': stats,
        'recent_requirements': recent_requirements,
        'approval_breakdown': approval_breakdown,
        'top_requesters': top_requesters,
    }
    
    return render(request, 'users/department_stats.html', context)


@login_required(login_url='users:login')
def user_management_view(request):
    """Admin user management dashboard - CRUD operations for users"""
    from django.contrib import messages
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods
    
    user = request.user
    
    # Check if user is admin
    if not user.is_admin_user():
        return redirect('users:dashboard')
    
    # Get all users
    all_users = CustomUser.objects.all().order_by('-created_at')
    
    # Filter by role if specified
    role_filter = request.GET.get('role', '')
    dept_filter = request.GET.get('department', '')
    search_query = request.GET.get('search', '')
    
    if role_filter:
        all_users = all_users.filter(role=role_filter)
    if dept_filter:
        all_users = all_users.filter(department=dept_filter)
    if search_query:
        all_users = all_users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(all_users, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # User statistics
    user_stats = {
        'total_users': CustomUser.objects.count(),
        'active_users': CustomUser.objects.filter(is_active=True).count(),
        'inactive_users': CustomUser.objects.filter(is_active=False).count(),
        'by_role': {
            'users': CustomUser.objects.filter(role='user').count(),
            'heads': CustomUser.objects.filter(role='head').count(),
            'admins': CustomUser.objects.filter(role='admin').count(),
            'cfos': CustomUser.objects.filter(role='cfo').count(),
            'ceos': CustomUser.objects.filter(role='ceo').count(),
        }
    }
    
    context = {
        'page_title': 'User Management',
        'page_obj': page_obj,
        'all_users': page_obj.object_list,
        'user_stats': user_stats,
        'role_choices': CustomUser.ROLE_CHOICES,
        'dept_choices': CustomUser.DEPARTMENT_CHOICES,
        'current_role': role_filter,
        'current_dept': dept_filter,
        'search_query': search_query,
    }
    
    return render(request, 'users/user_management.html', context)


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def user_edit_view(request, user_id):
    """Edit user details - admin only"""
    from django.contrib import messages
    
    user = request.user
    if not user.is_admin_user():
        return redirect('users:dashboard')
    
    target_user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        target_user.username = request.POST.get('username', target_user.username)
        target_user.email = request.POST.get('email', target_user.email)
        target_user.first_name = request.POST.get('first_name', target_user.first_name)
        target_user.last_name = request.POST.get('last_name', target_user.last_name)
        target_user.role = request.POST.get('role', target_user.role)
        target_user.department = request.POST.get('department', target_user.department)
        is_active = request.POST.get('is_active') == 'on'
        target_user.is_active = is_active
        
        try:
            target_user.save()
            messages.success(request, f'User {target_user.username} updated successfully!')
            AuditLog.objects.create(
                user=user,
                action='updated',
                details=f'Admin {user.get_full_name()} updated user {target_user.username} details'
            ) if 'AuditLog' in dir() else None
            return redirect('users:user_management')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'page_title': f'Edit User - {target_user.username}',
        'target_user': target_user,
        'role_choices': CustomUser.ROLE_CHOICES,
        'dept_choices': CustomUser.DEPARTMENT_CHOICES,
    }
    
    return render(request, 'users/user_edit.html', context)


@login_required(login_url='users:login')
@require_http_methods(["POST"])
def user_toggle_active_view(request, user_id):
    """Toggle user active status - admin only"""
    from django.contrib import messages
    from django.http import JsonResponse
    
    user = request.user
    if not user.is_admin_user():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    target_user = get_object_or_404(CustomUser, id=user_id)
    target_user.is_active = not target_user.is_active
    target_user.save()
    
    return JsonResponse({
        'success': True,
        'is_active': target_user.is_active,
        'message': f'User {target_user.username} is now {"active" if target_user.is_active else "inactive"}'
    })


@login_required(login_url='users:login')
@require_http_methods(["POST"])
def user_delete_view(request, user_id):
    """Delete user - admin only"""
    from django.contrib import messages
    
    user = request.user
    if not user.is_admin_user():
        messages.error(request, 'Unauthorized action')
        return redirect('users:user_management')
    
    target_user = get_object_or_404(CustomUser, id=user_id)
    username = target_user.username
    
    try:
        target_user.delete()
        messages.success(request, f'User {username} deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect('users:user_management')


@login_required(login_url='users:login')
def reports_view(request):
    """Admin reports and analytics dashboard"""
    from apps.requirements.models import Requirement
    from apps.approvals.models import Approval
    
    user = request.user
    
    # Check if user is admin
    if not user.is_admin_user():
        return redirect('users:dashboard')
    
    # Global statistics
    total_requirements = Requirement.objects.count()
    total_users = CustomUser.objects.count()
    # Count only requirements with final approval (CEO level approval that is approved)
    total_approvals = Approval.objects.filter(
        approval_level=4,
        status='approved'
    ).count()
    total_approved_cost = Requirement.objects.filter(
        status='approved'
    ).aggregate(total=Sum('estimated_cost'))['total'] or 0
    
    # Breakdown by status
    status_breakdown = {
        'pending': Requirement.objects.filter(status='pending').count(),
        'approved': Requirement.objects.filter(status='approved').count(),
        'rejected': Requirement.objects.filter(status='rejected').count(),
    }
    
    # Calculate status percentages
    status_percentages = {}
    if total_requirements > 0:
        status_percentages = {
            'pending': round((status_breakdown['pending'] / total_requirements) * 100, 1),
            'approved': round((status_breakdown['approved'] / total_requirements) * 100, 1),
            'rejected': round((status_breakdown['rejected'] / total_requirements) * 100, 1),
        }
    else:
        status_percentages = {'pending': 0, 'approved': 0, 'rejected': 0}
    
    # Breakdown by priority
    priority_breakdown = {
        'critical': Requirement.objects.filter(priority='critical').count(),
        'high': Requirement.objects.filter(priority='high').count(),
        'medium': Requirement.objects.filter(priority='medium').count(),
        'low': Requirement.objects.filter(priority='low').count(),
    }
    
    # Get department data properly (exclude executive departments)
    dept_stats = {}
    for dept_choice in Requirement._meta.get_field('department').choices:
        dept_code = dept_choice[0]
        dept_label = dept_choice[1]
        # Skip 'executive' department from performance metrics
        if dept_code == 'executive':
            continue
        count = Requirement.objects.filter(department=dept_code).count()
        cost = Requirement.objects.filter(
            department=dept_code,
            status='approved'
        ).aggregate(total=Sum('estimated_cost'))['total'] or 0
        dept_stats[dept_label] = {'count': count, 'cost': cost}
    
    # Top approvers
    top_approvers = Approval.objects.values(
        'approver__first_name',
        'approver__last_name'
    ).annotate(
        approved_count=Count('id', filter=Q(status='approved')),
        rejected_count=Count('id', filter=Q(status='rejected')),
        total_count=Count('id')
    ).order_by('-total_count')[:10]
    
    # Recent requirements
    recent_requirements = Requirement.objects.select_related(
        'requested_by'
    ).order_by('-created_date')[:10]
    
    # Approval trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_approvals = Approval.objects.filter(
        timestamp__gte=thirty_days_ago
    ).values('status').annotate(count=Count('id'))
    
    context = {
        'page_title': 'System Reports & Analytics',
        'total_requirements': total_requirements,
        'total_users': total_users,
        'total_approvals': total_approvals,
        'total_approved_cost': total_approved_cost,
        'status_breakdown': status_breakdown,
        'status_percentages': status_percentages,
        'priority_breakdown': priority_breakdown,
        'dept_stats': dept_stats,
        'top_approvers': top_approvers,
        'recent_requirements': recent_requirements,
        'recent_approvals': recent_approvals,
    }
    
    return render(request, 'users/reports.html', context)
