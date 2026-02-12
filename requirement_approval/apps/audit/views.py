from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q
from .models import AuditLog
from apps.requirements.models import Requirement
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from datetime import datetime


@login_required(login_url='users:login')
def audit_list_view(request):
    """List all requirements with their latest audit log for admin users only"""
    user = request.user
    
    # Only admins can access audit logs
    if not user.is_admin_user():
        from django.contrib import messages
        messages.error(request, 'You do not have permission to view audit logs.')
        return redirect('users:dashboard')
    
    # Get all unique requirements with their audit logs
    from django.db.models import Max
    
    requirements = Requirement.objects.all().order_by('-created_date')
    
    # Search and filter
    search_query = request.GET.get('search', '')
    requirement_filter = request.GET.get('requirement', '')
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    
    if search_query:
        requirements = requirements.filter(
            Q(item_description__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    if requirement_filter:
        requirements = requirements.filter(id=requirement_filter)
    
    if action_filter:
        # Filter requirements that have this action in their audit logs
        requirements = requirements.filter(audit_logs__action=action_filter).distinct()
    
    if user_filter:
        # Filter requirements that have audit logs from this user
        requirements = requirements.filter(audit_logs__user__id=user_filter).distinct()
    
    # Build list with latest audit log for each requirement
    requirements_with_audit = []
    for req in requirements:
        latest_audit = req.audit_logs.order_by('-timestamp').first()
        if latest_audit:
            requirements_with_audit.append({
                'requirement': req,
                'latest_audit': latest_audit,
            })
    
    # Get unique values for filter dropdowns
    all_actions = AuditLog.ACTION_CHOICES
    from apps.users.models import CustomUser
    admin_users = CustomUser.objects.filter(role='admin').order_by('first_name')
    
    context = {
        'requirements_with_audit': requirements_with_audit,
        'search_query': search_query,
        'requirement_filter': requirement_filter,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'actions': all_actions,
        'users': admin_users,
    }
    
    return render(request, 'audit/list_audit.html', context)


@login_required(login_url='users:login')
def audit_pdf_view(request, audit_id):
    """Generate PDF for a specific audit log with full requirement details"""
    user = request.user
    
    # Only admins can download audit PDFs
    if not user.is_admin_user():
        return HttpResponse('Unauthorized', status=403)
    
    audit_log = AuditLog.objects.select_related('requirement', 'user').get(id=audit_id)
    requirement = audit_log.requirement
    
    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="audit_REQ-{requirement.id}_{audit_id}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0052CC'),
        spaceAfter=12,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0052CC'),
        spaceAfter=8,
        spaceBefore=8,
    )
    
    # Title
    elements.append(Paragraph('Audit Log Report', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Requirement Details
    elements.append(Paragraph('Requirement Details', heading_style))
    
    req_data = [
        ['Requirement ID:', f'REQ-{requirement.id}'],
        ['Description:', requirement.item_description[:100]],
        ['Department:', requirement.get_department_display()],
        ['Priority:', requirement.get_priority_display()],
        ['Status:', requirement.get_status_display()],
        ['Type:', requirement.get_requirement_type_display()],
        ['Requested By:', requirement.requested_by.get_full_name()],
        ['Created Date:', requirement.created_date.strftime('%B %d, %Y')],
    ]
    
    req_table = Table(req_data, colWidths=[2*inch, 4*inch])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    elements.append(req_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Audit Log Entry - Include Created + Approval/Modification actions
    elements.append(Paragraph('Approval & Modification Decisions', heading_style))
    
    # Filter for created + approval/rejection/modification actions
    approval_logs = AuditLog.objects.filter(
        requirement=requirement,
        action__in=['created', 'approved', 'rejected', 'request_modification']
    ).order_by('-timestamp')
    
    if approval_logs.exists():
        approval_data = [['Date', 'Action', 'Officer', 'Comments']]
        
        # Create a style for table content
        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
        )
        
        for log in approval_logs:
            approve_timestamp = log.timestamp.strftime('%m/%d/%Y\n%H:%M')
            action_display = log.get_action_display()
            user_name = log.user.get_full_name()
            comments = (log.details if log.details else 'N/A').replace('\n', ' ')[:80]
            
            approval_data.append([
                approve_timestamp,
                action_display,
                user_name,
                Paragraph(comments, cell_style),
            ])
        
        approval_table = Table(approval_data, colWidths=[1.2*inch, 1.2*inch, 1.5*inch, 1.5*inch])
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0052CC')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(approval_table)
    else:
        elements.append(Paragraph('No approval decisions recorded yet.', styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    return response
